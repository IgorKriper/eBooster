"""Issue and consume short-lived tokens for the branded eBooster connect page.

The bot never publishes a raw subscription URL into Telegram inline buttons;
instead it issues a one-shot token, links the user to ``/connect?token=...``,
and the FastAPI page resolves the token into the deep link.  Tokens expire
after :attr:`Settings.connect_token_ttl_minutes` and can only be consumed
once.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.core.config import Settings
from eboost.core.time import as_utc, utcnow
from eboost.models import ConnectToken, User


def _generate_token() -> str:
    return secrets.token_urlsafe(32)


async def issue_connect_token(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
) -> ConnectToken:
    token_value = _generate_token()
    expires_at = utcnow() + timedelta(minutes=settings.connect_token_ttl_minutes)
    token = ConnectToken(
        user_id=user.id,
        token=token_value,
        expires_at=expires_at,
    )
    session.add(token)
    await session.flush()
    return token


async def get_token(session: AsyncSession, token_value: str) -> ConnectToken | None:
    result = await session.execute(select(ConnectToken).where(ConnectToken.token == token_value))
    return result.scalar_one_or_none()


def is_token_active(token: ConnectToken, *, now: datetime | None = None) -> bool:
    """Token is active iff it has not expired AND has not been consumed yet.

    Consumed tokens (``used_at`` set) must NOT be reusable within the TTL —
    that would leave the raw subscription URL exposed for the rest of the
    window after a single click and undermine the whole one-shot model
    described in the module docstring.
    """
    moment = now or utcnow()
    expires_at = as_utc(token.expires_at)
    if not expires_at or expires_at < moment:
        return False
    if token.used_at is not None:
        return False
    return True


async def consume_token(session: AsyncSession, token: ConnectToken) -> None:
    token.use_count += 1
    if token.used_at is None:
        token.used_at = utcnow()
    await session.flush()
