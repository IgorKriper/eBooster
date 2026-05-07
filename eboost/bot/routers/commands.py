"""Top-priority command router.

`/start` and `/admin` MUST always work, even from inside an FSM input state
(e.g. admin entering a Telegram ID, user typing a promo code). This router is
registered first so the slash commands are caught before any state-bound
handler tries to parse the message body as plain text. The router clears any
active FSM state and then forwards the update to the regular handlers via the
shared callable references — this way we don't have to duplicate the welcome /
admin-menu logic.
"""

from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

router = Router(name="priority_commands")


@router.message(CommandStart())
async def priority_start(
    message: Message,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    # Imported lazily to avoid an import cycle with eboost.bot.routers.common.
    from aiogram.filters import CommandObject

    from eboost.bot.routers import common as common_router
    from eboost.services import users

    await state.clear()
    args: str | None = None
    raw = (message.text or "").split(maxsplit=1)
    if len(raw) > 1:
        args = raw[1]
    user = await users.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        start_payload=args,
    )
    await common_router._send_welcome(message, user)


@router.message(Command("admin"))
async def priority_admin(message: Message, state: FSMContext) -> None:
    from eboost.bot.routers import admin as admin_router

    await state.clear()
    await admin_router.show_admin_menu(message)
