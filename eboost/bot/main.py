from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.memory import MemoryStorage

from eboost.bot.middleware import DbSessionMiddleware
from eboost.bot.routers import admin, commands, common
from eboost.core.branding import BOT_LONG_DESCRIPTION, BOT_SHORT_DESCRIPTION
from eboost.core.config import get_settings
from eboost.db.init import create_sqlite_schema_for_local_dev
from eboost.db.session import async_session_maker
from eboost.services.bootstrap import seed_defaults

logger = logging.getLogger(__name__)


async def on_startup() -> None:
    await create_sqlite_schema_for_local_dev()
    async with async_session_maker() as session:
        await seed_defaults(session)
        await session.commit()


async def _push_bot_descriptions(bot: Bot) -> None:
    """Best-effort sync of pre-/post-start descriptions visible to Telegram users."""
    settings = get_settings()
    short = settings.bot_short_description or BOT_SHORT_DESCRIPTION
    long_text = settings.bot_long_description or BOT_LONG_DESCRIPTION
    try:
        await bot.set_my_short_description(short)
    except Exception:
        logger.exception("set_my_short_description failed")
    try:
        await bot.set_my_description(long_text)
    except Exception:
        logger.exception("set_my_description failed")


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = get_settings()
    if settings.bot_token == "change-me":
        raise RuntimeError("Set BOT_TOKEN in .env")

    telegram_session = AiohttpSession(proxy=settings.telegram_proxy or None)
    bot = Bot(token=settings.bot_token, session=telegram_session)
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.update.middleware(DbSessionMiddleware())
    # Priority router: /start and /admin always clear FSM state and bypass
    # admin numeric-input parsing. Must be registered BEFORE admin/common.
    dispatcher.include_router(commands.router)
    dispatcher.include_router(admin.router)
    dispatcher.include_router(common.router)
    await on_startup()
    await _push_bot_descriptions(bot)
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
