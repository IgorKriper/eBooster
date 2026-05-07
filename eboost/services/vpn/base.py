from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime


class VpnProvider(ABC):
    @abstractmethod
    async def create_user(self, *, telegram_id: int, subscription_until: datetime | None) -> str:
        raise NotImplementedError

    @abstractmethod
    async def extend_user(self, *, vpn_user_id: str, subscription_until: datetime | None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def disable_user(self, *, vpn_user_id: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get_subscription_url(self, *, vpn_user_id: str) -> str:
        raise NotImplementedError
