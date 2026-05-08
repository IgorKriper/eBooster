from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.core.config import Settings
from eboost.core.time import as_utc, utcnow
from eboost.models import ConnectToken, User


def _generate_token() -> str:
    return secrets.token_urlsafe(32)[:64]


async def issue_connect_token(
    session: AsyncSession,
    *,
    user: User,
    settings: Settings,
) -> ConnectToken:
    """Issue a new ConnectToken for the user.

    Old tokens are not deleted; they simply expire. The most recently issued
    token is the one we hand the user.
    """
    ttl = max(int(settings.connect_token_ttl_minutes), 1)
    token = ConnectToken(
        user_id=user.id,
        token=_generate_token(),
        expires_at=utcnow() + timedelta(minutes=ttl),
    )
    session.add(token)
    await session.flush()
    return token


async def consume_connect_token(
    session: AsyncSession,
    *,
    token_value: str,
) -> tuple[ConnectToken, User] | None:
    """Look up a ConnectToken; return None if missing/expired/used."""
    if not token_value:
        return None
    result = await session.execute(
        select(ConnectToken).where(ConnectToken.token == token_value)
    )
    token = result.scalar_one_or_none()
    if token is None:
        return None
    expires_at = as_utc(token.expires_at)
    if expires_at is None or expires_at <= utcnow():
        return None
    if token.used_at is not None:
        return None
    user = await session.get(User, token.user_id)
    if user is None:
        return None
    return token, user


async def mark_token_used(session: AsyncSession, *, token: ConnectToken) -> None:
    token.used_at = utcnow()
    await session.flush()
