from __future__ import annotations

import hashlib
import hmac

import aiohttp

from eboost.core.config import Settings


def connect_token(settings: Settings, telegram_id: int) -> str:
    secret = settings.bot_token or settings.yookassa_secret_key or "eboost"
    digest = hmac.new(
        secret.encode("utf-8"),
        f"happ:{telegram_id}".encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest[:32]


def connect_url(settings: Settings, telegram_id: int) -> str:
    base_url = settings.backend_public_url.rstrip("/")
    token = connect_token(settings, telegram_id)
    return f"{base_url}/api/happ/connect/{telegram_id}?token={token}"


async def encrypted_link(settings: Settings, subscription_url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post(
            settings.happ_crypto_api_url,
            json={"url": subscription_url},
            timeout=15,
        ) as response:
            text = (await response.text()).strip()
            if response.status >= 400:
                raise RuntimeError(f"Happ crypto failed: {response.status} {text}")

    link = text.strip().strip('"')
    if not link.startswith("happ://crypt5/"):
        raise RuntimeError("Happ crypto response does not contain crypt5 link")
    return link
