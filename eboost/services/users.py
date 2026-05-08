from __future__ import annotations

import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.models import User
from eboost.services import logs


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    result = await session.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def get_user_by_referral_code(session: AsyncSession, referral_code: str) -> User | None:
    result = await session.execute(select(User).where(User.referral_code == referral_code))
    return result.scalar_one_or_none()


async def generate_referral_code(session: AsyncSession) -> str:
    for _ in range(20):
        code = secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()
        if await get_user_by_referral_code(session, code) is None:
            return code
    raise RuntimeError("Could not generate unique referral code")


async def get_or_create_user(
    session: AsyncSession,
    *,
    telegram_id: int,
    username: str | None,
    first_name: str | None,
    start_payload: str | None = None,
) -> User:
    user = await get_user_by_telegram_id(session, telegram_id)
    if user:
        user.username = username
        user.first_name = first_name
        return user

    referrer_id = None
    if start_payload:
        referrer = await get_user_by_referral_code(session, start_payload.strip().upper())
        if referrer and referrer.telegram_id != telegram_id:
            referrer_id = referrer.id

    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        referral_code=await generate_referral_code(session),
        referrer_id=referrer_id,
    )
    session.add(user)
    await session.flush()
    await logs.system_log(session, event="user_registered", user_id=user.id, details={"telegram_id": telegram_id})
    return user
