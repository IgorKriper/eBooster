from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from eboost.core.time import utcnow
from eboost.core.config import Settings
from eboost.models import Payment, Referral, User
from eboost.models.payment import PaymentStatus
from eboost.models.referral import ReferralBonusType
from eboost.services import logs, subscriptions
from eboost.services.vpn.base import VpnProvider


@dataclass(frozen=True)
class ReferralStats:
    invited_count: int
    activated_count: int
    paid_count: int
    bonus_days: int
    friends_until_bonus: int


async def count_referrals(session: AsyncSession, referrer_id: int) -> int:
    result = await session.execute(select(func.count(User.id)).where(User.referrer_id == referrer_id))
    return int(result.scalar_one())


async def referral_stats(session: AsyncSession, *, referrer_id: int, settings: Settings) -> ReferralStats:
    invited_count = await count_referrals(session, referrer_id)
    activated_count = await _activated_referral_count(session, referrer_id)
    paid_count = await _paid_referral_count(session, referrer_id)
    bonus_days = await _referral_bonus_days(session, referrer_id)
    remainder = activated_count % settings.ref_friends_for_bonus
    friends_until_bonus = settings.ref_friends_for_bonus - remainder if remainder else settings.ref_friends_for_bonus
    return ReferralStats(
        invited_count=invited_count,
        activated_count=activated_count,
        paid_count=paid_count,
        bonus_days=bonus_days,
        friends_until_bonus=friends_until_bonus,
    )


async def award_referral_bonus(
    session: AsyncSession,
    *,
    referred: User,
    bonus_type: str,
    settings: Settings,
    vpn_provider: VpnProvider,
    source_payment_id: int | None = None,
) -> bool:
    if not referred.referrer_id or referred.referrer_id == referred.id:
        return False

    result = await session.execute(
        select(Referral).where(Referral.referred_id == referred.id, Referral.bonus_type == bonus_type)
    )
    if result.scalar_one_or_none():
        return False

    referrer = await session.get(User, referred.referrer_id)
    if not referrer or referrer.id == referred.id:
        return False

    bonus_days = settings.ref_trial_bonus_days if bonus_type == ReferralBonusType.TRIAL else settings.ref_payment_bonus_days
    bonus_days = await _allowed_bonus_days(
        session,
        referrer=referrer,
        requested_days=bonus_days,
        bonus_type=bonus_type,
        settings=settings,
    )
    if bonus_days <= 0:
        return False

    subscriptions.extend_subscription(referrer, bonus_days)
    referrer.bonus_days += bonus_days
    await subscriptions.sync_vpn_access(referrer, vpn_provider)

    session.add(
        Referral(
            referrer_id=referrer.id,
            referred_id=referred.id,
            bonus_type=bonus_type,
            bonus_days=bonus_days,
            source_payment_id=source_payment_id,
        )
    )
    await logs.system_log(
        session,
        event="referral_bonus_awarded",
        user_id=referrer.id,
        details={"referred_id": referred.id, "bonus_type": bonus_type, "bonus_days": bonus_days},
    )
    if bonus_type == ReferralBonusType.TRIAL:
        await award_milestone_bonus(
            session,
            referrer=referrer,
            referred=referred,
            settings=settings,
            vpn_provider=vpn_provider,
        )
    return True


async def award_milestone_bonus(
    session: AsyncSession,
    *,
    referrer: User,
    referred: User,
    settings: Settings,
    vpn_provider: VpnProvider,
) -> bool:
    activated_count = await _activated_referral_count(session, referrer.id)
    if activated_count == 0 or activated_count % settings.ref_friends_for_bonus != 0:
        return False

    milestone_count = await _bonus_count(session, referrer.id, ReferralBonusType.MILESTONE)
    expected_milestone_count = activated_count // settings.ref_friends_for_bonus
    if milestone_count >= expected_milestone_count:
        return False

    bonus_days = await _allowed_bonus_days(
        session,
        referrer=referrer,
        requested_days=settings.ref_payment_bonus_days,
        bonus_type=ReferralBonusType.MILESTONE,
        settings=settings,
    )
    if bonus_days <= 0:
        return False

    subscriptions.extend_subscription(referrer, bonus_days)
    referrer.bonus_days += bonus_days
    await subscriptions.sync_vpn_access(referrer, vpn_provider)
    session.add(
        Referral(
            referrer_id=referrer.id,
            referred_id=referred.id,
            bonus_type=ReferralBonusType.MILESTONE,
            bonus_days=bonus_days,
        )
    )
    await logs.system_log(
        session,
        event="referral_bonus_awarded",
        user_id=referrer.id,
        details={"referred_id": referred.id, "bonus_type": ReferralBonusType.MILESTONE, "bonus_days": bonus_days},
    )
    return True


async def _activated_referral_count(session: AsyncSession, referrer_id: int) -> int:
    result = await session.execute(
        select(func.count(User.id)).where(User.referrer_id == referrer_id, User.trial_started_at.is_not(None))
    )
    return int(result.scalar_one())


async def _paid_referral_count(session: AsyncSession, referrer_id: int) -> int:
    result = await session.execute(
        select(func.count(func.distinct(Payment.user_id)))
        .join(User, User.id == Payment.user_id)
        .where(User.referrer_id == referrer_id, Payment.status == PaymentStatus.SUCCEEDED)
    )
    return int(result.scalar_one())


async def _bonus_count(session: AsyncSession, referrer_id: int, bonus_type: str) -> int:
    result = await session.execute(
        select(func.count(Referral.id)).where(Referral.referrer_id == referrer_id, Referral.bonus_type == bonus_type)
    )
    return int(result.scalar_one())


async def _referral_bonus_days(session: AsyncSession, referrer_id: int) -> int:
    result = await session.execute(
        select(func.coalesce(func.sum(Referral.bonus_days), 0)).where(Referral.referrer_id == referrer_id)
    )
    return int(result.scalar_one())


async def _paid_days(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(Payment)
        .options(selectinload(Payment.plan))
        .where(Payment.user_id == user_id, Payment.status == PaymentStatus.SUCCEEDED)
    )
    return sum(payment.plan.duration_days for payment in result.scalars().all())


async def _trial_bonus_days_today(session: AsyncSession, referrer_id: int) -> int:
    now = utcnow()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.coalesce(func.sum(Referral.bonus_days), 0)).where(
            Referral.referrer_id == referrer_id,
            Referral.bonus_type == ReferralBonusType.TRIAL,
            Referral.created_at >= day_start,
            Referral.created_at < day_start + timedelta(days=1),
        )
    )
    return int(result.scalar_one())


async def _allowed_bonus_days(
    session: AsyncSession,
    *,
    referrer: User,
    requested_days: int,
    bonus_type: str,
    settings: Settings,
) -> int:
    allowed_days = requested_days

    if bonus_type == ReferralBonusType.TRIAL:
        trial_left_today = settings.ref_trial_daily_bonus_limit_days - await _trial_bonus_days_today(session, referrer.id)
        allowed_days = min(allowed_days, max(trial_left_today, 0))

    paid_days = await _paid_days(session, referrer.id)
    current_bonus_days = await _referral_bonus_days(session, referrer.id)
    if paid_days <= 0:
        cap = settings.ref_unpaid_bonus_cap_days
    else:
        cap = paid_days * settings.ref_paid_bonus_percent_limit // 100

    bonus_left = cap - current_bonus_days
    return min(allowed_days, max(bonus_left, 0))
