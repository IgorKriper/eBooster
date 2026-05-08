from __future__ import annotations

from datetime import datetime
from hashlib import sha256

from eboost.core.config import Settings
from eboost.services.vpn.base import VpnProvider


class MockVpnProvider(VpnProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_user(self, *, telegram_id: int, subscription_until: datetime | None, device_limit: int = 5) -> str:
        return f"mock-vpn-{telegram_id}"

    async def extend_user(self, *, vpn_user_id: str, subscription_until: datetime | None) -> None:
        return None

    async def disable_user(self, *, vpn_user_id: str) -> None:
        return None

    async def get_subscription_url(self, *, vpn_user_id: str) -> str:
        token = sha256(f"{vpn_user_id}:{self.settings.vpn_keys}".encode()).hexdigest()[:24]
        return f"https://mock-vpn.eboost.local/sub/{vpn_user_id}?token={token}"
