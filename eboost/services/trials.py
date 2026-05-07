from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from eboost.core.config import Settings
from eboost.core.time import utcnow
from eboost.models import User
from eboost.models.referral import ReferralBonusType
from eboost.services import referrals, subscriptions
from eboost.services.vpn.base import VpnProvider


async def activate_trial(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
    vpn_provider: VpnProvider,
) -> tuple[bool, str]:
    if user.trial_started_at:
        return False, "Пробный доступ уже был активирован."

    user.trial_started_at = utcnow()
    subscriptions.extend_subscription(user, settings.trial_days)
    await subscriptions.sync_vpn_access(user, vpn_provider)
    await referrals.award_referral_bonus(
        session,
        referred=user,
        bonus_type=ReferralBonusType.TRIAL,
        settings=settings,
        vpn_provider=vpn_provider,
    )
    return True, f"Пробный доступ активирован на {settings.trial_days} дня."
