from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.core.time import as_utc, utcnow
from eboost.models import Payment, PromoCode, PromoCodeUsage, User
from eboost.models.payment import PaymentStatus


@dataclass(frozen=True)
class PromoValidation:
    is_valid: bool
    promo_code: PromoCode | None = None
    reason: str = ""


async def find_promo_code(session: AsyncSession, code: str) -> PromoCode | None:
    normalized = code.strip().upper()
    result = await session.execute(select(PromoCode).where(func.upper(PromoCode.code) == normalized))
    return result.scalar_one_or_none()


async def user_has_successful_payment(session: AsyncSession, user_id: int) -> bool:
    result = await session.execute(
        select(func.count(Payment.id)).where(Payment.user_id == user_id, Payment.status == PaymentStatus.SUCCEEDED)
    )
    return int(result.scalar_one()) > 0


async def validate_promo_code(session: AsyncSession, *, user: User, code: str) -> PromoValidation:
    promo_code = await find_promo_code(session, code)
    if not promo_code or not promo_code.is_active:
        return PromoValidation(False, reason="Промокод не найден или недоступен")

    now = utcnow()
    valid_from = as_utc(promo_code.valid_from)
    valid_until = as_utc(promo_code.valid_until)
    if valid_from and valid_from > now:
        return PromoValidation(False, reason="Промокод пока недоступен")
    if valid_until and valid_until < now:
        return PromoValidation(False, reason="Срок действия промокода закончился")
    if promo_code.max_uses is not None and promo_code.used_count >= promo_code.max_uses:
        return PromoValidation(False, reason="Промокод уже использован максимальное число раз")
    if promo_code.first_payment_only and await user_has_successful_payment(session, user.id):
        return PromoValidation(False, reason="Промокод доступен только на первую оплату")

    result = await session.execute(
        select(PromoCodeUsage).where(PromoCodeUsage.promo_code_id == promo_code.id, PromoCodeUsage.user_id == user.id)
    )
    if result.scalar_one_or_none():
        return PromoValidation(False, reason="Ты уже использовал этот промокод")

    return PromoValidation(True, promo_code=promo_code)


def apply_discount(amount: int, discount_percent: int) -> int:
    return amount * (100 - discount_percent) // 100


async def seed_promo_codes(session: AsyncSession) -> None:
    if await find_promo_code(session, "WELCOME30") is None:
        session.add(PromoCode(code="WELCOME30", discount_percent=30, first_payment_only=True))
