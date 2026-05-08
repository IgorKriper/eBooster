from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

import aiohttp

from eboost.core.config import Settings
from eboost.services.vpn.base import VpnProvider


class MarzbanVpnProvider(VpnProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._access_token: str | None = None

    async def create_user(self, *, telegram_id: int, subscription_until: datetime | None, device_limit: int = 5) -> str:
        username = self._username(telegram_id)
        payload = self._user_payload(
            username=username,
            telegram_id=telegram_id,
            subscription_until=subscription_until,
            device_limit=device_limit,
            include_username=True,
        )

        try:
            data = await self._request("POST", "/api/user", json_payload=payload)
        except RuntimeError as exc:
            if "409" not in str(exc):
                raise
            await self.extend_user(vpn_user_id=username, subscription_until=subscription_until)
            data = await self._request("GET", f"/api/user/{username}")
        return str(data.get("username") or username)

    async def extend_user(self, *, vpn_user_id: str, subscription_until: datetime | None) -> None:
        payload = {
            "status": "active",
            "expire": self._expire(subscription_until),
            "data_limit": self.settings.marzban_data_limit_gb * 1024 * 1024 * 1024,
            "data_limit_reset_strategy": self.settings.marzban_data_limit_reset_strategy,
        }
        if self.settings.marzban_inbounds:
            payload["inbounds"] = self._inbounds()
        await self._request("PUT", f"/api/user/{vpn_user_id}", json_payload=payload)

    async def disable_user(self, *, vpn_user_id: str) -> None:
        await self._request("PUT", f"/api/user/{vpn_user_id}", json_payload={"status": "disabled"})

    async def get_subscription_url(self, *, vpn_user_id: str) -> str:
        data = await self._request("GET", f"/api/user/{vpn_user_id}")
        subscription_url = data.get("subscription_url")
        if subscription_url:
            return self._absolute_subscription_url(str(subscription_url))
        links = data.get("links")
        if isinstance(links, list) and links:
            return str(links[0])
        raise RuntimeError("Marzban response does not contain subscription_url")

    async def get_system_stats(self) -> dict[str, Any]:
        return await self._request("GET", "/api/system")

    async def get_nodes(self) -> list[dict[str, Any]]:
        data = await self._request("GET", "/api/nodes")
        nodes = data.get("items") or data.get("nodes") or data.get("data") or data
        if isinstance(nodes, list):
            return [node for node in nodes if isinstance(node, dict)]
        return []

    async def get_nodes_usage(self, *, start: datetime, end: datetime) -> dict[str, Any]:
        query = urlencode({"start": start.isoformat(), "end": end.isoformat()})
        path = f"/api/nodes/usage?{query}"
        return await self._request("GET", path)

    async def get_hosts(self) -> dict[str, Any]:
        return await self._request("GET", "/api/hosts")

    async def update_hosts(self, hosts: dict[str, Any]) -> None:
        await self._request("PUT", "/api/hosts", json_payload=hosts)

    async def _request(self, method: str, path: str, json_payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.settings.marzban_base_url:
            raise RuntimeError("Set MARZBAN_BASE_URL to use Marzban VPN provider")
        token = await self._token()
        url = f"{self.settings.marzban_base_url.rstrip('/')}/{path.lstrip('/')}"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.request(method, url, json=json_payload, timeout=60) as response:
                if response.status == 401 and self._access_token:
                    self._access_token = None
                    return await self._request(method, path, json_payload=json_payload)
                data = await self._response_data(response)
                if response.status >= 400:
                    raise RuntimeError(f"Marzban request failed: {response.status} {data}")
                return data

    async def _token(self) -> str:
        if self._access_token:
            return self._access_token
        if not self.settings.marzban_admin_username or not self.settings.marzban_admin_password:
            raise RuntimeError("Set MARZBAN_ADMIN_USERNAME and MARZBAN_ADMIN_PASSWORD")
        url = f"{self.settings.marzban_base_url.rstrip('/')}/api/admin/token"
        form = aiohttp.FormData()
        form.add_field("username", self.settings.marzban_admin_username)
        form.add_field("password", self.settings.marzban_admin_password)
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=form, timeout=60) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"Marzban auth failed: {response.status} {data}")
        self._access_token = str(data["access_token"])
        return self._access_token

    async def _response_data(self, response: aiohttp.ClientResponse) -> dict[str, Any]:
        if response.status == 204:
            return {}
        try:
            data = await response.json(content_type=None)
        except Exception:
            text = await response.text()
            return {"text": text}
        return data if isinstance(data, dict) else {"data": data}

    def _user_payload(
        self,
        *,
        username: str,
        telegram_id: int,
        subscription_until: datetime | None,
        device_limit: int,
        include_username: bool,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "status": "active",
            "proxies": self._proxies(),
            "expire": self._expire(subscription_until),
            "data_limit": self.settings.marzban_data_limit_gb * 1024 * 1024 * 1024,
            "data_limit_reset_strategy": self.settings.marzban_data_limit_reset_strategy,
            "note": f"eBooster Telegram ID: {telegram_id}; device limit: {device_limit}",
        }
        if include_username:
            payload["username"] = username
        if self.settings.marzban_inbounds:
            payload["inbounds"] = self._inbounds()
        return payload

    def _username(self, telegram_id: int) -> str:
        username = f"eboost_{telegram_id}"
        username = re.sub(r"[^a-z0-9_]", "_", username.lower())
        return username[:32]

    def _expire(self, value: datetime | None) -> int:
        if value is None:
            return 0
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return int(value.astimezone(timezone.utc).timestamp())

    def _proxies(self) -> dict[str, dict[str, Any]]:
        proxies: dict[str, dict[str, Any]] = {}
        for protocol in self.settings.marzban_proxies.split(","):
            protocol = protocol.strip().lower()
            if protocol:
                proxies[protocol] = {}
        return proxies or {"vless": {}}

    def _inbounds(self) -> dict[str, list[str]]:
        inbounds: dict[str, list[str]] = {}
        for item in self.settings.marzban_inbounds.split(";"):
            protocol, sep, values = item.partition(":")
            if not sep:
                continue
            tags = [value.strip() for value in values.split(",") if value.strip()]
            if tags:
                inbounds[protocol.strip().lower()] = tags
        return inbounds

    def _absolute_subscription_url(self, url: str) -> str:
        if url.startswith("http://") or url.startswith("https://"):
            return url
        return f"{self.settings.marzban_base_url.rstrip('/')}/{url.lstrip('/')}"
