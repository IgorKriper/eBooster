from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.core.config import Settings
from eboost.models import Referral, User
from eboost.models.referral import ReferralBonusType
from eboost.services import subscriptions
from eboost.services.vpn.base import VpnProvider


async def count_referrals(session: AsyncSession, referrer_id: int) -> int:
    result = await session.execute(select(func.count(User.id)).where(User.referrer_id == referrer_id))
    return int(result.scalar_one())


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
    return True
