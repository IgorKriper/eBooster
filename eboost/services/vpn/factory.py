from __future__ import annotations

from eboost.core.config import Settings
from eboost.services.vpn.base import VpnProvider
from eboost.services.vpn.http import HttpVpnProvider
from eboost.services.vpn.mock import MockVpnProvider


def get_vpn_provider(settings: Settings) -> VpnProvider:
    if settings.vpn_provider == "mock":
        return MockVpnProvider(settings)
    if settings.vpn_provider == "http":
        return HttpVpnProvider(settings)
    raise ValueError(f"Unsupported VPN provider: {settings.vpn_provider}")
