from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from eboost.core.config import Settings
from eboost.core.time import utcnow
from eboost.models import Payment, Plan, PromoCodeUsage, User
from eboost.models.payment import PaymentStatus
from eboost.models.referral import ReferralBonusType
from eboost.services import promo_codes, referrals, subscriptions
from eboost.services.payment.base import PaymentCreateRequest, PaymentProvider, PaymentWebhookResult
from eboost.services.vpn.base import VpnProvider


async def create_payment(
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
        promo_code_id=selected_promo.id if selected_promo else None,
        provider=payment_provider.name,
        status=PaymentStatus.PENDING,
        original_amount=plan.price_rub,
        discount_percent=discount_percent,
        final_amount=final_amount,
    )
    session.add(payment)
    await session.flush()

    result = await payment_provider.create_payment(
        PaymentCreateRequest(
            payment_id=payment.id,
            user_id=user.id,
            amount_rub=payment.final_amount,
            description=plan.title,
        )
    )
    payment.external_id = result.external_id
    payment.payment_url = result.payment_url
    return payment


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
    subscriptions.extend_subscription(payment.user, payment.plan.duration_days)
    await subscriptions.sync_vpn_access(payment.user, vpn_provider)

    if payment.promo_code_id and payment.promo_code:
        payment.promo_code.used_count += 1
        session.add(
            PromoCodeUsage(
                promo_code_id=payment.promo_code_id,
                user_id=payment.user_id,
                payment_id=payment.id,
            )
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
