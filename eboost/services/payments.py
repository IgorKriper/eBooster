from __future__ import annotations

import hashlib
import hmac

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from eboost.core.config import Settings
from eboost.core.time import utcnow
from eboost.models import Payment, Plan, PromoCodeUsage, User
from eboost.models.payment import PaymentStatus
from eboost.models.referral import ReferralBonusType
from eboost.services import logs, promo_codes, referrals, subscriptions
from eboost.services.payment.base import PaymentCreateRequest, PaymentProvider, PaymentWebhookResult
from eboost.services.vpn.base import VpnProvider


async def create_payment(
    session: AsyncSession,
    *,
    user: User,
    plan: Plan,
    payment_provider: PaymentProvider,
    promo_code: str | None = None,
    customer_email: str | None = None,
) -> Payment:
    payment = await _create_payment_record(
        session,
        user=user,
        plan=plan,
        payment_provider=payment_provider,
        promo_code=promo_code,
    )
    await _send_payment_to_provider(
        session,
        payment=payment,
        payment_provider=payment_provider,
        customer_email=customer_email,
    )
    return payment


async def create_deferred_payment(
    session: AsyncSession,
    *,
    user: User,
    plan: Plan,
    payment_provider: PaymentProvider,
    settings: Settings,
    promo_code: str | None = None,
) -> Payment:
    payment = await _create_payment_record(
        session,
        user=user,
        plan=plan,
        payment_provider=payment_provider,
        promo_code=promo_code,
    )
    payment.payment_url = checkout_url(settings, payment.id)
    return payment


async def _create_payment_record(
    session: AsyncSession,
    *,
    user: User,
    plan: Plan,
    payment_provider: PaymentProvider,
    promo_code: str | None = None,
) -> Payment:
    discount_percent = 0
    selected_promo = None
    if promo_code:
        validation = await promo_codes.validate_promo_code(session, user=user, code=promo_code)
        if not validation.is_valid or validation.promo_code is None:
            raise ValueError(validation.reason)
        selected_promo = validation.promo_code
        discount_percent = selected_promo.discount_percent

    final_amount = promo_codes.apply_discount(plan.price_rub, discount_percent)
    payment = Payment(
        user_id=user.id,
        plan_id=plan.id,
        user=user,
        plan=plan,
        promo_code_id=selected_promo.id if selected_promo else None,
        provider=payment_provider.name,
        status=PaymentStatus.CREATED,
        original_amount=plan.price_rub,
        discount_percent=discount_percent,
        final_amount=final_amount,
    )
    session.add(payment)
    await session.flush()
    return payment


async def _send_payment_to_provider(
    session: AsyncSession,
    *,
    payment: Payment,
    payment_provider: PaymentProvider,
    customer_email: str | None = None,
) -> None:
    try:
        result = await payment_provider.create_payment(
            PaymentCreateRequest(
                payment_id=payment.id,
                user_id=payment.user_id,
                amount_rub=payment.final_amount,
                description=payment.plan.title if payment.plan else "eBooster",
                customer_email=customer_email,
            )
        )
    except Exception as exc:
        await logs.system_log(session, event="payment_error", user_id=payment.user_id, details={"error": str(exc)})
        raise
    payment.external_id = result.external_id
    payment.provider_payment_id = result.external_id
    payment.payment_url = result.payment_url
    payment.status = PaymentStatus.PENDING


async def start_deferred_provider_payment(
    session: AsyncSession,
    *,
    payment: Payment,
    payment_provider: PaymentProvider,
    customer_email: str,
) -> Payment:
    if payment.external_id and payment.payment_url:
        return payment
    await _send_payment_to_provider(
        session,
        payment=payment,
        payment_provider=payment_provider,
        customer_email=customer_email,
    )
    return payment


def checkout_url(settings: Settings, payment_id: int) -> str:
    base_url = settings.backend_public_url.rstrip("/")
    return f"{base_url}/pay/{payment_id}?token={checkout_token(settings, payment_id)}"


def checkout_token(settings: Settings, payment_id: int) -> str:
    secret = settings.bot_token or settings.yookassa_secret_key or "eboost"
    digest = hmac.new(
        secret.encode("utf-8"),
        f"payment:{payment_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:32]


async def get_payment_for_user(session: AsyncSession, *, payment_id: int, user_id: int) -> Payment | None:
    result = await session.execute(
        select(Payment)
        .options(selectinload(Payment.plan))
        .where(Payment.id == payment_id, Payment.user_id == user_id)
    )
    return result.scalar_one_or_none()


async def list_user_payments(session: AsyncSession, user_id: int, limit: int = 10) -> list[Payment]:
    result = await session.execute(
        select(Payment)
        .options(selectinload(Payment.plan))
        .where(Payment.user_id == user_id)
        .order_by(Payment.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def complete_payment(
    session: AsyncSession,
    *,
    payment_id: int,
    status: str,
    settings: Settings,
    vpn_provider: VpnProvider,
    amount_rub: int | None = None,
    currency: str | None = None,
) -> Payment:
    result = await session.execute(
        select(Payment)
        .options(selectinload(Payment.user), selectinload(Payment.plan), selectinload(Payment.promo_code))
        .where(Payment.id == payment_id)
    )
    payment = result.scalar_one_or_none()
    if payment is None:
        raise ValueError("Payment not found")
    if payment.status == PaymentStatus.SUCCEEDED:
        return payment

    if status != PaymentStatus.SUCCEEDED:
        payment.status = status
        return payment

    if currency and currency != "RUB":
        raise ValueError("Payment currency mismatch")
    if amount_rub is not None and amount_rub != payment.final_amount:
        raise ValueError("Payment amount mismatch")

    payment.status = PaymentStatus.SUCCEEDED
    payment.paid_at = utcnow()
    had_vpn_user = bool(payment.user.vpn_user_id)
    if payment.plan.is_device_pack:
        payment.user.device_limit = max(int(payment.user.device_limit or 0), 0) + max(
            int(payment.plan.bonus_devices or 0), 0
        )
    else:
        subscriptions.extend_subscription(payment.user, payment.plan.duration_days)
        # TZ v2: subscription buy/extend grants the tariff's slot count.
        # Never downgrade — keep extra slots earned via add-ons.
        plan_slots = int(payment.plan.slot_devices or 0)
        if plan_slots > 0:
            payment.user.device_limit = max(int(payment.user.device_limit or 0), plan_slots)
    try:
        await subscriptions.sync_vpn_access(payment.user, vpn_provider)
    except Exception as exc:
        await logs.system_log(session, event="vpn_error", user_id=payment.user_id, details={"error": str(exc)})
        raise
    await logs.system_log(
        session,
        event="payment_paid",
        user_id=payment.user_id,
        details={"payment_id": payment.id, "provider_payment_id": payment.provider_payment_id, "amount": payment.final_amount},
    )
    if payment.plan.is_device_pack:
        await logs.system_log(
            session,
            event="device_pack_purchased",
            user_id=payment.user_id,
            details={
                "bonus_devices": payment.plan.bonus_devices,
                "device_limit": payment.user.device_limit,
            },
        )
    else:
        await logs.system_log(
            session,
            event="subscription_extended",
            user_id=payment.user_id,
            details={"days": payment.plan.duration_days, "subscription_until": payment.user.subscription_until},
        )
    await logs.system_log(
        session,
        event="vpn_access_extended" if had_vpn_user else "vpn_access_created",
        user_id=payment.user_id,
        details={"vpn_user_id": payment.user.vpn_user_id, "device_limit": payment.user.device_limit},
    )

    if payment.promo_code_id and payment.promo_code:
        payment.promo_code.used_count += 1
        session.add(
            PromoCodeUsage(
                promo_code_id=payment.promo_code_id,
                user_id=payment.user_id,
                payment_id=payment.id,
            )
        )
        await logs.system_log(
            session,
            event="promo_applied",
            user_id=payment.user_id,
            details={"payment_id": payment.id, "promo_code_id": payment.promo_code_id},
        )

    await referrals.award_referral_bonus(
        session,
        referred=payment.user,
        bonus_type=ReferralBonusType.PAYMENT,
        settings=settings,
        vpn_provider=vpn_provider,
        source_payment_id=payment.id,
    )
    return payment


async def handle_provider_webhook(
    session: AsyncSession,
    *,
    webhook: PaymentWebhookResult,
    settings: Settings,
    vpn_provider: VpnProvider,
) -> Payment:
    return await complete_payment(
        session,
        payment_id=webhook.payment_id,
        status=webhook.status,
        settings=settings,
        vpn_provider=vpn_provider,
        amount_rub=webhook.amount_rub,
        currency=webhook.currency,
    )
