from __future__ import annotations

from datetime import timedelta

from eboost.core.time import as_utc, utcnow
from eboost.models import User
from eboost.services.vpn.base import VpnProvider


def is_subscription_active(user: User) -> bool:
    subscription_until = as_utc(user.subscription_until)
    return bool(subscription_until and subscription_until > utcnow() and not user.is_disabled)


def extend_subscription(user: User, days: int) -> None:
    subscription_until = as_utc(user.subscription_until)
    base = subscription_until if subscription_until and subscription_until > utcnow() else utcnow()
    user.subscription_until = base + timedelta(days=days)
    user.is_disabled = False


async def sync_vpn_access(user: User, vpn_provider: VpnProvider) -> None:
    try:
        if not user.vpn_user_id:
            user.vpn_user_id = await vpn_provider.create_user(
                telegram_id=user.telegram_id,
                subscription_until=user.subscription_until,
                device_limit=user.device_limit,
            )
        else:
            await vpn_provider.extend_user(vpn_user_id=user.vpn_user_id, subscription_until=user.subscription_until)
        user.vpn_subscription_url = await vpn_provider.get_subscription_url(vpn_user_id=user.vpn_user_id)
    except Exception as exc:
        raise RuntimeError(f"VPN sync failed for user {user.id}: {exc}") from exc


async def disable_access(user: User, vpn_provider: VpnProvider) -> None:
    user.is_disabled = True
    try:
        if user.vpn_user_id:
            await vpn_provider.disable_user(vpn_user_id=user.vpn_user_id)
    except Exception as exc:
        raise RuntimeError(f"VPN disable failed for user {user.id}: {exc}") from exc
