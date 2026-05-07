"""Admin panel.

The router exposes both the legacy slash commands (``/stats``, ``/user 123``,
``/give 123 30`` …) and a new button-based menu wired through
:class:`AdminFlow` FSM states. The FSM input states (waiting for a Telegram ID
or a day count) all show ``⬅️ Назад`` / ``❌ Отмена`` buttons, and any
``/start`` or ``/admin`` issued from inside an input state is intercepted by
``commands.py`` which clears the FSM first — so they are never parsed as a
Telegram ID.
"""

from __future__ import annotations

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.bot import keyboards
from eboost.bot.formatters import format_date, user_status
from eboost.bot.states import AdminFlow
from eboost.core.branding import BRAND_NAME
from eboost.core.config import get_settings
from eboost.models import Payment, User
from eboost.models.payment import PaymentStatus
from eboost.services import referrals, subscriptions, users
from eboost.services.vpn.factory import get_vpn_provider

router = Router(name="admin")


def parse_int(value: str) -> int | None:
    text = (value or "").strip()
    if not text or text.startswith("/"):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_id_set


async def require_admin_message(message: Message) -> bool:
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администратору.")
        return False
    return True


async def require_admin_callback(callback: CallbackQuery) -> bool:
    if not is_admin(callback.from_user.id):
        await callback.answer("Команда доступна только администратору.", show_alert=True)
        return False
    return True


# ---------------------------------------------------------------------------
# Slash commands kept for backwards compatibility


async def show_admin_menu(message: Message) -> None:
    """Render the root admin menu (used by both /admin and the priority
    commands router after FSM cleanup)."""
    if not is_admin(message.from_user.id):
        await message.answer("Команда доступна только администратору.")
        return
    await message.answer(
        f"⚙️ Админ-панель {BRAND_NAME}\n\nВыбери раздел:",
        reply_markup=keyboards.admin_root_menu(),
    )


@router.message(Command("admin"))
async def admin_menu_command(message: Message, state: FSMContext) -> None:
    await state.clear()
    await show_admin_menu(message)


@router.message(Command("stats"))
async def stats(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    await message.answer(await _format_global_stats(session))


@router.message(Command("user"))
async def user_info(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /user <telegram_id>")
        return
    telegram_id = parse_int(parts[1])
    if telegram_id is None:
        await message.answer("Telegram ID должен быть числом.")
        return
    await _send_user_card(message, session, telegram_id)


@router.message(Command("give"))
async def give_days(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
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
    await _apply_give_days(message, session, telegram_id=telegram_id, days=days)


@router.message(Command("disable"))
async def disable_user_cmd(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: /disable <telegram_id>")
        return
    telegram_id = parse_int(parts[1])
    if telegram_id is None:
        await message.answer("Telegram ID должен быть числом.")
        return
    await _apply_disable(message, session, telegram_id=telegram_id)


@router.message(Command("broadcast"))
async def broadcast(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not await require_admin_message(message):
        return
    text = (message.text or "").removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Формат: /broadcast <text>")
        return
    sent = await _send_broadcast(session, bot, text)
    await message.answer(f"Отправлено: {sent}")


# ---------------------------------------------------------------------------
# Inline-button menu


@router.callback_query(F.data == "admin:menu")
async def admin_root(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    try:
        await callback.message.edit_text(
            f"⚙️ Админ-панель {BRAND_NAME}\n\nВыбери раздел:",
            reply_markup=keyboards.admin_root_menu(),
        )
    except Exception:
        await callback.message.answer(
            f"⚙️ Админ-панель {BRAND_NAME}",
            reply_markup=keyboards.admin_root_menu(),
        )
    await callback.answer()


@router.callback_query(F.data == "admin:cancel")
async def admin_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text(
        f"⚙️ Админ-панель {BRAND_NAME}\n\nДействие отменено.",
        reply_markup=keyboards.admin_root_menu(),
    )
    await callback.answer("Отменено")


@router.callback_query(F.data == "admin:stats")
async def admin_stats(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback):
        return
    text = await _format_global_stats(session)
    await callback.message.edit_text(text, reply_markup=keyboards.admin_back_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:user")
async def admin_user_request(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminFlow.waiting_user_id)
    await callback.message.edit_text(
        "👤 Введи Telegram ID пользователя:",
        reply_markup=keyboards.admin_input_menu(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_user_id)
async def admin_user_id_received(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if not await require_admin_message(message):
        await state.clear()
        return
    if (message.text or "").startswith("/"):
        # Slash commands are handled by the priority router; ignore here.
        return
    telegram_id = parse_int(message.text or "")
    if telegram_id is None:
        await message.answer(
            "Telegram ID должен быть числом. Попробуй ещё раз или нажми «Отмена».",
            reply_markup=keyboards.admin_input_menu(),
        )
        return
    await state.clear()
    await _send_user_card(message, session, telegram_id)
    await message.answer(
        "Готово.", reply_markup=keyboards.admin_back_menu()
    )


@router.callback_query(F.data == "admin:give")
async def admin_give_request(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminFlow.waiting_give_id)
    await callback.message.edit_text(
        "🎁 Введи Telegram ID пользователя, которому выдать бонусные дни:",
        reply_markup=keyboards.admin_input_menu(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_give_id)
async def admin_give_id_received(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if not await require_admin_message(message):
        await state.clear()
        return
    if (message.text or "").startswith("/"):
        return
    telegram_id = parse_int(message.text or "")
    if telegram_id is None:
        await message.answer(
            "Telegram ID должен быть числом. Попробуй ещё раз или нажми «Отмена».",
            reply_markup=keyboards.admin_input_menu(),
        )
        return
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "Пользователь не найден.", reply_markup=keyboards.admin_back_menu()
        )
        await state.clear()
        return
    await state.update_data(give_telegram_id=telegram_id)
    await state.set_state(AdminFlow.waiting_give_days)
    await message.answer(
        f"Сколько дней выдать пользователю {telegram_id}? Введи число:",
        reply_markup=keyboards.admin_input_menu(),
    )


@router.message(AdminFlow.waiting_give_days)
async def admin_give_days_received(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if not await require_admin_message(message):
        await state.clear()
        return
    if (message.text or "").startswith("/"):
        return
    days = parse_int(message.text or "")
    if days is None or days <= 0:
        await message.answer(
            "Введи положительное число дней или нажми «Отмена».",
            reply_markup=keyboards.admin_input_menu(),
        )
        return
    data = await state.get_data()
    telegram_id = data.get("give_telegram_id")
    await state.clear()
    if telegram_id is None:
        await message.answer(
            "Сессия сброшена, попробуй ещё раз.", reply_markup=keyboards.admin_back_menu()
        )
        return
    await _apply_give_days(
        message, session, telegram_id=int(telegram_id), days=days
    )


@router.callback_query(F.data == "admin:disable")
async def admin_disable_request(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminFlow.waiting_disable_id)
    await callback.message.edit_text(
        "🛑 Введи Telegram ID пользователя, у которого отключить доступ:",
        reply_markup=keyboards.admin_input_menu(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_disable_id)
async def admin_disable_id_received(
    message: Message, session: AsyncSession, state: FSMContext
) -> None:
    if not await require_admin_message(message):
        await state.clear()
        return
    if (message.text or "").startswith("/"):
        return
    telegram_id = parse_int(message.text or "")
    if telegram_id is None:
        await message.answer(
            "Telegram ID должен быть числом. Попробуй ещё раз или нажми «Отмена».",
            reply_markup=keyboards.admin_input_menu(),
        )
        return
    await state.clear()
    await _apply_disable(message, session, telegram_id=telegram_id)


@router.callback_query(F.data == "admin:broadcast")
async def admin_broadcast_request(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminFlow.waiting_broadcast_text)
    await callback.message.edit_text(
        "📣 Отправь текст рассылки одним сообщением (поддерживается markdown).",
        reply_markup=keyboards.admin_input_menu(),
    )
    await callback.answer()


@router.message(AdminFlow.waiting_broadcast_text)
async def admin_broadcast_received(
    message: Message, session: AsyncSession, state: FSMContext, bot: Bot
) -> None:
    if not await require_admin_message(message):
        await state.clear()
        return
    if (message.text or "").startswith("/"):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer(
            "Текст не может быть пустым. Попробуй ещё раз или нажми «Отмена».",
            reply_markup=keyboards.admin_input_menu(),
        )
        return
    await state.clear()
    sent = await _send_broadcast(session, bot, text)
    await message.answer(
        f"Рассылка отправлена: {sent} получателям.",
        reply_markup=keyboards.admin_back_menu(),
    )


# ---------------------------------------------------------------------------
# Referral statistics


@router.callback_query(F.data == "admin:referrals")
async def admin_referrals(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback):
        return
    stats = await referrals.list_referrer_stats(session, limit=20)
    if not stats:
        await callback.message.edit_text(
            "📊 Рефералы\n\nПока никто не приводил пользователей.",
            reply_markup=keyboards.admin_back_menu(),
        )
        await callback.answer()
        return
    lines = ["📊 Рефералы — топ", ""]
    for index, item in enumerate(stats, start=1):
        lines.append(
            f"{index}. {item.display_label}\n"
            f"   trial: {item.trial_activations} · 1-я оплата: {item.first_payments} · "
            f"продл.: {item.renewal_payments} · год: {item.yearly_payments}"
        )
    items = [(item.referrer_id, item.display_label) for item in stats]
    await callback.message.edit_text(
        "\n".join(lines), reply_markup=keyboards.admin_referrers_menu(items)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:ref:"))
async def admin_referrer_detail(
    callback: CallbackQuery, session: AsyncSession
) -> None:
    if not await require_admin_callback(callback):
        return
    referrer_id_str = callback.data.split(":", 2)[2]
    try:
        referrer_id = int(referrer_id_str)
    except ValueError:
        await callback.answer("Некорректный ID", show_alert=True)
        return
    item = await referrals.get_referrer_stats(session, referrer_id)
    if item is None:
        await callback.answer("Реферер не найден", show_alert=True)
        return
    text = (
        f"📊 Реферер {item.display_label}\n\n"
        f"Telegram ID: {item.telegram_id}\n"
        f"Приглашено всего: {item.invited_total}\n"
        f"Из них платящих: {item.invited_paying}\n"
        f"Активаций trial: {item.trial_activations}\n"
        f"Первых оплат: {item.first_payments}\n"
        f"Продлений: {item.renewal_payments}\n"
        f"Годовых: {item.yearly_payments}\n"
        f"Выручка по факту: {item.revenue_rub}₽"
    )
    await callback.message.edit_text(
        text, reply_markup=keyboards.admin_back_menu("admin:referrals")
    )
    await callback.answer()


# ---------------------------------------------------------------------------
# Helpers shared between slash commands and the new FSM


async def _format_global_stats(session: AsyncSession) -> str:
    users_count = await session.scalar(select(func.count(User.id)))
    payments_count = await session.scalar(select(func.count(Payment.id)))
    paid_amount = await session.scalar(
        select(func.coalesce(func.sum(Payment.final_amount), 0)).where(
            Payment.status == PaymentStatus.SUCCEEDED
        )
    )
    return (
        f"📊 Статистика {BRAND_NAME}\n\n"
        f"Пользователи: {users_count}\n"
        f"Платежи: {payments_count}\n"
        f"Оплачено по факту: {paid_amount}₽"
    )


async def _send_user_card(
    message: Message, session: AsyncSession, telegram_id: int
) -> None:
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "Пользователь не найден.", reply_markup=keyboards.admin_back_menu()
        )
        return
    username = f"@{user.username}" if user.username else "—"
    await message.answer(
        f"Telegram ID: {user.telegram_id}\n"
        f"Username: {username}\n"
        f"Статус: {user_status(user)}\n"
        f"Доступ до: {format_date(user)}\n"
        f"📱 Лимит устройств: {user.device_limit}\n"
        f"Реферальный код: {user.referral_code}\n"
        f"🎁 Бонусные дни: {user.bonus_days}",
    )


async def _apply_give_days(
    message: Message,
    session: AsyncSession,
    *,
    telegram_id: int,
    days: int,
) -> None:
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "Пользователь не найден.", reply_markup=keyboards.admin_back_menu()
        )
        return
    settings = get_settings()
    vpn_provider = get_vpn_provider(settings)
    subscriptions.extend_subscription(user, days)
    user.bonus_days += days
    await subscriptions.sync_vpn_access(user, vpn_provider)
    await message.answer(
        f"Готово. Доступ до: {format_date(user)}",
        reply_markup=keyboards.admin_back_menu(),
    )


async def _apply_disable(
    message: Message, session: AsyncSession, *, telegram_id: int
) -> None:
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        await message.answer(
            "Пользователь не найден.", reply_markup=keyboards.admin_back_menu()
        )
        return
    settings = get_settings()
    await subscriptions.disable_access(user, get_vpn_provider(settings))
    await message.answer(
        "Доступ отключён.", reply_markup=keyboards.admin_back_menu()
    )


async def _send_broadcast(
    session: AsyncSession, bot: Bot, text: str
) -> int:
    result = await session.execute(select(User.telegram_id))
    sent = 0
    for telegram_id in result.scalars().all():
        try:
            await bot.send_message(telegram_id, text)
            sent += 1
        except Exception:
            continue
    return sent
