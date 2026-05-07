from __future__ import annotations

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.bot.formatters import format_date, user_status
from eboost.core.config import get_settings
from eboost.models import Payment, User
from eboost.models.payment import PaymentStatus
from eboost.services import subscriptions, users
from eboost.services.vpn.factory import get_vpn_provider

router = Router()


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_id_set


async def require_admin(message: Message) -> bool:
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администратору.")
        return False
    return True


@router.message(Command("admin"))
async def admin_menu(message: Message) -> None:
    if not await require_admin(message):
        return
    await message.answer(
        "Админ-команды:\n"
        "/stats\n"
        "/user <telegram_id>\n"
        "/give <telegram_id> <days>\n"
        "/disable <telegram_id>\n"
        "/broadcast <text>"
    )


@router.message(Command("stats"))
async def stats(message: Message, session: AsyncSession) -> None:
    if not await require_admin(message):
        return
    users_count = await session.scalar(select(func.count(User.id)))
    payments_count = await session.scalar(select(func.count(Payment.id)))
    paid_amount = await session.scalar(
        select(func.coalesce(func.sum(Payment.final_amount), 0)).where(Payment.status == PaymentStatus.SUCCEEDED)
    )
    await message.answer(f"Пользователи: {users_count}\nПлатежи: {payments_count}\nОплачено: {paid_amount}₽")


@router.message(Command("user"))
async def user_info(message: Message, session: AsyncSession) -> None:
    if not await require_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /user <telegram_id>")
        return
    telegram_id = parse_int(parts[1])
    if telegram_id is None:
        await message.answer("Telegram ID должен быть числом.")
        return
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return
    username = f"@{user.username}" if user.username else "-"
    await message.answer(
        f"Telegram ID: {user.telegram_id}\n"
        f"Username: {username}\n"
        f"Статус: {user_status(user)}\n"
        f"Доступ до: {format_date(user)}\n"
        f"Реферальный код: {user.referral_code}\n"
        f"Бонусные дни: {user.bonus_days}"
    )


@router.message(Command("give"))
async def give_days(message: Message, session: AsyncSession) -> None:
    if not await require_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3:
        await message.answer("Формат: /give <telegram_id> <days>")
        return
    telegram_id = parse_int(parts[1])
    days = parse_int(parts[2])
    if telegram_id is None or days is None:
        await message.answer("Telegram ID и days должны быть числами.")
        return
    if days <= 0:
        await message.answer("Количество дней должно быть больше 0.")
        return
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return
    settings = get_settings()
    vpn_provider = get_vpn_provider(settings)
    subscriptions.extend_subscription(user, days)
    user.bonus_days += days
    await subscriptions.sync_vpn_access(user, vpn_provider)
    await message.answer(f"Готово. Доступ до: {format_date(user)}")


@router.message(Command("disable"))
async def disable_user(message: Message, session: AsyncSession) -> None:
    if not await require_admin(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /disable <telegram_id>")
        return
    telegram_id = parse_int(parts[1])
    if telegram_id is None:
        await message.answer("Telegram ID должен быть числом.")
        return
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer("Пользователь не найден.")
        return
    settings = get_settings()
    await subscriptions.disable_access(user, get_vpn_provider(settings))
    await message.answer("Доступ отключён.")


@router.message(Command("broadcast"))
async def broadcast(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not await require_admin(message):
        return
    text = (message.text or "").removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Формат: /broadcast <text>")
        return
    result = await session.execute(select(User.telegram_id))
    sent = 0
    for telegram_id in result.scalars().all():
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            continue
    await message.answer(f"Отправлено: {sent}")
