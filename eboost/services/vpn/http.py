from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import aiohttp

from eboost.core.config import Settings
from eboost.services.vpn.base import VpnProvider


class HttpVpnProvider(VpnProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_user(self, *, telegram_id: int, subscription_until: datetime | None, device_limit: int = 5) -> str:
        payload = self._render_payload(
            self.settings.http_vpn_create_payload,
            default={
                "telegram_id": telegram_id,
                "subscription_until": self._iso(subscription_until),
                "device_limit": device_limit,
            },
            telegram_id=telegram_id,
            subscription_until=self._iso(subscription_until),
            device_limit=device_limit,
        )
        data = await self._request("POST", self.settings.http_vpn_create_path, json_payload=payload)
        user_id = self._get_field(data, self.settings.http_vpn_user_id_field)
        if not user_id:
            raise RuntimeError(f"HTTP VPN response does not contain {self.settings.http_vpn_user_id_field}")
        return str(user_id)

    async def extend_user(self, *, vpn_user_id: str, subscription_until: datetime | None) -> None:
        payload = self._render_payload(
            self.settings.http_vpn_extend_payload,
            default={"subscription_until": self._iso(subscription_until)},
            vpn_user_id=vpn_user_id,
            subscription_until=self._iso(subscription_until),
        )
        await self._request(
            "POST",
            self.settings.http_vpn_extend_path.format(vpn_user_id=vpn_user_id),
            json_payload=payload,
        )

    async def disable_user(self, *, vpn_user_id: str) -> None:
        await self._request("POST", self.settings.http_vpn_disable_path.format(vpn_user_id=vpn_user_id))

    async def get_subscription_url(self, *, vpn_user_id: str) -> str:
        data = await self._request("GET", self.settings.http_vpn_subscription_path.format(vpn_user_id=vpn_user_id))
        subscription_url = self._get_field(data, self.settings.http_vpn_subscription_url_field)
        if not subscription_url:
            raise RuntimeError(
                f"HTTP VPN response does not contain {self.settings.http_vpn_subscription_url_field}"
            )
        return str(subscription_url)

    async def _request(self, method: str, path: str, json_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.settings.http_vpn_base_url:
            raise RuntimeError("Set HTTP_VPN_BASE_URL to use HTTP VPN provider")

        url = f"{self.settings.http_vpn_base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        if self.settings.http_vpn_token:
            headers["Authorization"] = f"Bearer {self.settings.http_vpn_token}"

        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.request(method, url, json=json_payload, timeout=60) as response:
                if response.status == 204:
                    return {}
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"HTTP VPN request failed: {response.status} {data}")
                return data if isinstance(data, dict) else {"data": data}

    def _render_payload(
        self,
        template: str,
        *,
        default: dict[str, Any],
        **values: str | int | None,
    ) -> dict[str, Any]:
        if not template:
            return default
        rendered = template
        for key, value in values.items():
            rendered = rendered.replace("{" + key + "}", str(value or ""))
        return json.loads(rendered)

    def _get_field(self, data: dict[str, Any], field_path: str) -> Any:
        value: Any = data
        for part in field_path.split("."):
            if not isinstance(value, dict):
                return None
            value = value.get(part)
        return value

    def _iso(self, value: datetime | None) -> str | None:
        return value.isoformat() if value else None
