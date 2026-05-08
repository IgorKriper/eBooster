from __future__ import annotations

import html
from datetime import timedelta

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.bot import keyboards
from eboost.bot.formatters import format_date, user_status
from eboost.bot.states import AdminBroadcastFlow, AdminPromoFlow, AdminUserFlow
from eboost.core.config import get_settings
from eboost.core.time import as_utc, utcnow
from eboost.models import Payment, PromoCode, PromoCodeUsage, Referral, User
from eboost.models.payment import PaymentStatus
from eboost.services import logs, server_load, subscriptions, users
from eboost.services.vpn.factory import get_vpn_provider

router = Router()

DENIED = "⛔ Команда недоступна"


def parse_int(value: str) -> int | None:
    try:
        return int(value)
    except ValueError:
        return None


def is_admin(telegram_id: int) -> bool:
    return telegram_id in get_settings().admin_id_set


async def require_admin_message(message: Message) -> bool:
    if not is_admin(message.from_user.id):
        await message.answer(DENIED)
        return False
    return True


async def require_admin_callback(callback: CallbackQuery) -> bool:
    if not is_admin(callback.from_user.id):
        await callback.answer(DENIED, show_alert=True)
        return False
    return True


@router.callback_query(F.data == "admin")
async def admin_callback(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("<b>🛠 Админ-панель</b>\n\nВыбери действие:", reply_markup=keyboards.admin_menu())
    await callback.answer()


@router.message(Command("admin"))
async def admin_menu_command(message: Message) -> None:
    if not await require_admin_message(message):
        return
    await message.answer("<b>🛠 Админ-панель</b>\n\nВыбери действие:", reply_markup=keyboards.admin_menu())


@router.callback_query(F.data == "admin:stats")
async def admin_stats_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback):
        return
    await callback.message.edit_text(await _stats_text(session), reply_markup=keyboards.back_menu("admin"))
    await callback.answer()


@router.message(Command("stats"))
async def stats_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    await message.answer(await _stats_text(session))


@router.callback_query(F.data == "admin:servers")
async def admin_servers(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("<b>🌍 Серверы</b>\n\nВыбери действие:", reply_markup=keyboards.admin_servers_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:servers_load")
async def admin_servers_load(callback: CallbackQuery, session: AsyncSession, bot: Bot) -> None:
    if not await require_admin_callback(callback):
        return
    states = await server_load.refresh_server_loads(bot, session)
    await callback.message.edit_text(server_load.format_server_loads(states), reply_markup=keyboards.admin_servers_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:servers_disable")
async def admin_servers_disable(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback):
        return
    states = await server_load.ensure_server_states(session)
    buttons = [(state.code, state.name, state.is_enabled) for state in states]
    await callback.message.edit_text(
        "<b>🚫 Отключить сервер</b>\n\nНажми на сервер, чтобы переключить статус:",
        reply_markup=keyboards.admin_server_toggle_menu(buttons),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("admin:server_toggle:"))
async def admin_server_toggle(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback):
        return
    _, _, code, action = callback.data.split(":", 3)
    state = await server_load.set_server_enabled(
        session,
        code=code,
        enabled=action == "enable",
        admin_id=callback.from_user.id,
    )
    if state is None:
        await callback.answer("Сервер не найден", show_alert=True)
        return
    states = await server_load.ensure_server_states(session)
    buttons = [(item.code, item.name, item.is_enabled) for item in states]
    status = "включён" if state.is_enabled else "отключён"
    await callback.message.edit_text(
        f"<b>🌍 Серверы</b>\n\n{state.name}: <b>{status}</b>",
        reply_markup=keyboards.admin_server_toggle_menu(buttons),
    )
    await callback.answer()


async def _stats_text(session: AsyncSession) -> str:
    now = utcnow()
    users_count = await session.scalar(select(func.count(User.id)))
    active_subscriptions = await session.scalar(
        select(func.count(User.id)).where(
            User.subscription_until.is_not(None),
            User.subscription_until > now,
            User.is_disabled.is_(False),
        )
    )
    paid_user_ids = select(Payment.user_id).where(Payment.status == PaymentStatus.SUCCEEDED).distinct()
    active_trials = await session.scalar(
        select(func.count(User.id)).where(
            User.trial_started_at.is_not(None),
            User.subscription_until.is_not(None),
            User.subscription_until > now,
            User.is_disabled.is_(False),
            User.id.not_in(paid_user_ids),
        )
    )
    payments_count = await session.scalar(
        select(func.count(Payment.id)).where(Payment.status == PaymentStatus.SUCCEEDED)
    )
    revenue = await session.scalar(
        select(func.coalesce(func.sum(Payment.final_amount), 0)).where(Payment.status == PaymentStatus.SUCCEEDED)
    )
    promo_uses = await session.scalar(select(func.count(PromoCodeUsage.id)))
    referrals_count = await session.scalar(select(func.count(Referral.id)))
    return (
        "<b>📊 Статистика eBooster</b>\n\n"
        f"Пользователей: <b>{users_count or 0}</b>\n"
        f"Активных подписок: <b>{active_subscriptions or 0}</b>\n"
        f"Пробных доступов: <b>{active_trials or 0}</b>\n"
        f"Оплат: <b>{payments_count or 0}</b>\n"
        f"Выручка: <b>{revenue or 0}₽</b>\n"
        f"Промокодов использовано: <b>{promo_uses or 0}</b>\n"
        f"Реферальных приглашений: <b>{referrals_count or 0}</b>"
    )


@router.callback_query(F.data == "admin:promos")
async def admin_promos(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("<b>🎟 Промокоды</b>\n\nВыбери действие:", reply_markup=keyboards.admin_promos_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:promo_create")
async def promo_create_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    await state.set_state(AdminPromoFlow.waiting_code)
    await callback.message.edit_text("<b>➕ Создать промокод</b>\n\nВведи код.\nНапример: <code>BOOST30</code>")
    await callback.answer()


@router.message(AdminPromoFlow.waiting_code)
async def promo_create_code(message: Message, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    code = (message.text or "").strip().upper()
    if not code:
        await message.answer("Введи код промокода.")
        return
    await state.update_data(code=code)
    await state.set_state(AdminPromoFlow.waiting_discount)
    await message.answer("Введи процент скидки.\nНапример: <code>20</code> или <code>30</code>")


@router.message(AdminPromoFlow.waiting_discount)
async def promo_create_discount(message: Message, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    discount = parse_int((message.text or "").strip())
    if discount is None or discount <= 0 or discount >= 100:
        await message.answer("Скидка должна быть числом от 1 до 99.")
        return
    await state.update_data(discount=discount)
    await state.set_state(AdminPromoFlow.waiting_valid_days)
    await message.answer("Введи срок действия в днях.\nНапример: <code>3</code>")


@router.message(AdminPromoFlow.waiting_valid_days)
async def promo_create_valid_days(message: Message, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    valid_days = parse_int((message.text or "").strip())
    if valid_days is None or valid_days <= 0:
        await message.answer("Срок должен быть числом больше 0.")
        return
    await state.update_data(valid_days=valid_days)
    await state.set_state(AdminPromoFlow.waiting_limit)
    await message.answer("Введи лимит использований.\nНапример: <code>100</code>")


@router.message(AdminPromoFlow.waiting_limit)
async def promo_create_limit(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    limit = parse_int((message.text or "").strip())
    if limit is None or limit <= 0:
        await message.answer("Лимит должен быть числом больше 0.")
        return
    data = await state.get_data()
    code = data["code"]
    discount = int(data["discount"])
    valid_until = utcnow() + timedelta(days=int(data["valid_days"]))

    result = await session.execute(select(PromoCode).where(func.upper(PromoCode.code) == code))
    promo = result.scalar_one_or_none()
    if promo is None:
        promo = PromoCode(code=code, discount_percent=discount, first_payment_only=True)
        session.add(promo)
    promo.discount_percent = discount
    promo.max_uses = limit
    promo.valid_from = utcnow()
    promo.valid_until = valid_until
    promo.first_payment_only = True
    promo.is_active = True
    await logs.admin_log(
        session,
        admin_id=message.from_user.id,
        action="promo_created",
        details={"code": code, "discount": discount, "limit": limit, "valid_until": valid_until},
    )
    await state.clear()
    await message.answer(
        "<b>🎟 Промокод создан</b>\n\n"
        f"Код: <code>{html.escape(code)}</code>\n"
        f"Скидка: <b>{discount}%</b>\n"
        f"Действует до: <b>{valid_until.strftime('%d.%m.%Y')}</b>\n"
        f"Лимит: <b>{limit}</b>",
        reply_markup=keyboards.admin_promos_menu(),
    )


@router.callback_query(F.data == "admin:promo_list")
async def promo_list_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    if not await require_admin_callback(callback):
        return
    await callback.message.edit_text(await _promo_list_text(session), reply_markup=keyboards.admin_promos_menu())
    await callback.answer()


@router.message(Command("promos"))
async def promos_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    await message.answer(await _promo_list_text(session))


async def _promo_list_text(session: AsyncSession) -> str:
    result = await session.execute(select(PromoCode).order_by(PromoCode.id.desc()).limit(30))
    promo_codes = list(result.scalars().all())
    if not promo_codes:
        return "<b>🎟 Промокоды</b>\n\nПромокодов пока нет."
    rows = []
    for promo in promo_codes:
        status = "активен" if promo.is_active else "выключен"
        limit = promo.max_uses if promo.max_uses is not None else "без лимита"
        until = as_utc(promo.valid_until)
        until_text = until.strftime("%d.%m.%Y") if until else "-"
        rows.append(
            f"<code>{html.escape(promo.code)}</code> - {promo.discount_percent}% - {status} - "
            f"{promo.used_count}/{limit} - до {until_text}"
        )
    return "<b>🎟 Промокоды</b>\n\n" + "\n".join(rows)


@router.callback_query(F.data == "admin:promo_disable")
async def promo_disable_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminPromoFlow.waiting_disable_code)
    await callback.message.edit_text("<b>❌ Отключить промокод</b>\n\nВведи код промокода:")
    await callback.answer()


@router.message(AdminPromoFlow.waiting_disable_code)
async def promo_disable_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    code = (message.text or "").strip().upper()
    result = await session.execute(select(PromoCode).where(func.upper(PromoCode.code) == code))
    promo = result.scalar_one_or_none()
    if not promo:
        await message.answer("Промокод не найден.", reply_markup=keyboards.admin_promos_menu())
        await state.clear()
        return
    promo.is_active = False
    await logs.admin_log(
        session,
        admin_id=message.from_user.id,
        action="promo_disabled",
        details={"code": promo.code},
    )
    await state.clear()
    await message.answer(f"Промокод <code>{html.escape(promo.code)}</code> отключён.", reply_markup=keyboards.admin_promos_menu())


@router.callback_query(F.data == "admin:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("<b>📢 Рассылка</b>\n\nВыбери сегмент:", reply_markup=keyboards.admin_broadcast_segments_menu())
    await callback.answer()


@router.callback_query(F.data.startswith("admin:broadcast_segment:"))
async def broadcast_segment(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    segment = callback.data.rsplit(":", 1)[1]
    await state.update_data(segment=segment)
    await state.set_state(AdminBroadcastFlow.waiting_text)
    await callback.message.edit_text("<b>📢 Рассылка</b>\n\nВведи текст сообщения:")
    await callback.answer()


@router.message(AdminBroadcastFlow.waiting_text)
async def broadcast_text(message: Message, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    text = (message.text or "").strip()
    if not text:
        await message.answer("Текст не должен быть пустым.")
        return
    await state.update_data(text=text)
    await state.set_state(AdminBroadcastFlow.confirming)
    await message.answer(
        "<b>📢 Предпросмотр рассылки</b>\n\n"
        f"{html.escape(text)}\n\n"
        "Отправить?",
        reply_markup=keyboards.admin_broadcast_confirm_menu(),
    )


@router.callback_query(F.data == "admin:broadcast_cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.clear()
    await callback.message.edit_text("<b>📢 Рассылка отменена</b>", reply_markup=keyboards.admin_menu())
    await callback.answer()


@router.callback_query(F.data == "admin:broadcast_send")
async def broadcast_send(callback: CallbackQuery, session: AsyncSession, state: FSMContext, bot: Bot) -> None:
    if not await require_admin_callback(callback):
        return
    data = await state.get_data()
    text = data.get("text")
    segment = data.get("segment")
    if not text or not segment:
        await callback.answer("Рассылка не готова", show_alert=True)
        return
    recipients = await _broadcast_recipients(session, segment)
    sent = 0
    for telegram_id in recipients:
        try:
            await bot.send_message(telegram_id, text, parse_mode=None)
            sent += 1
        except Exception:
            continue
    await state.clear()
    await logs.admin_log(
        session,
        admin_id=callback.from_user.id,
        action="broadcast_sent",
        details={"segment": segment, "sent": sent},
    )
    await callback.message.edit_text(f"<b>📢 Рассылка отправлена</b>\n\nОтправлено: <b>{sent}</b>", reply_markup=keyboards.admin_menu())
    await callback.answer()


async def _broadcast_recipients(session: AsyncSession, segment: str) -> list[int]:
    now = utcnow()
    paid_user_ids = select(Payment.user_id).where(Payment.status == PaymentStatus.SUCCEEDED).distinct()
    if segment == "all":
        query = select(User.telegram_id)
    elif segment == "no_trial":
        query = select(User.telegram_id).where(User.trial_started_at.is_(None), User.id.not_in(paid_user_ids))
    elif segment == "trial_no_payment":
        query = select(User.telegram_id).where(User.trial_started_at.is_not(None), User.id.not_in(paid_user_ids))
    elif segment == "expired":
        query = select(User.telegram_id).where(User.subscription_until.is_not(None), User.subscription_until <= now)
    elif segment == "active_paid":
        query = select(User.telegram_id).where(
            User.id.in_(paid_user_ids),
            User.subscription_until.is_not(None),
            User.subscription_until > now,
            User.is_disabled.is_(False),
        )
    else:
        return []
    result = await session.execute(query)
    return list(result.scalars().all())


@router.callback_query(F.data == "admin:user")
async def admin_user_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminUserFlow.waiting_user_id)
    await callback.message.edit_text("<b>👤 Пользователь</b>\n\nВведи Telegram ID:")
    await callback.answer()


@router.message(AdminUserFlow.waiting_user_id)
async def admin_user_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    telegram_id = parse_int((message.text or "").strip())
    if telegram_id is None:
        await message.answer("Telegram ID должен быть числом.")
        return
    await state.clear()
    await message.answer(await _user_text(session, telegram_id), reply_markup=keyboards.admin_menu())


@router.message(Command("user"))
async def user_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or parse_int(parts[1]) is None:
        await message.answer("Формат: <code>/user telegram_id</code>")
        return
    await message.answer(await _user_text(session, int(parts[1])))


async def _user_text(session: AsyncSession, telegram_id: int) -> str:
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        return "Пользователь не найден."
    username = f"@{user.username}" if user.username else "-"
    return (
        "<b>👤 Пользователь</b>\n\n"
        f"Telegram ID: <code>{user.telegram_id}</code>\n"
        f"Username: <code>{html.escape(username)}</code>\n"
        f"Статус: <b>{user_status(user)}</b>\n"
        f"Доступ до: <b>{format_date(user)}</b>\n"
        f"Реферальный код: <code>{html.escape(user.referral_code)}</code>\n"
        f"Бонусные дни: <b>{user.bonus_days}</b>"
    )


@router.callback_query(F.data == "admin:give")
async def give_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminUserFlow.waiting_give_user_id)
    await callback.message.edit_text("<b>⚙️ Выдать доступ</b>\n\nВведи Telegram ID:")
    await callback.answer()


@router.message(AdminUserFlow.waiting_give_user_id)
async def give_user_id(message: Message, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    telegram_id = parse_int((message.text or "").strip())
    if telegram_id is None:
        await message.answer("Telegram ID должен быть числом.")
        return
    await state.update_data(telegram_id=telegram_id)
    await state.set_state(AdminUserFlow.waiting_give_days)
    await message.answer("Сколько дней выдать?")


@router.message(AdminUserFlow.waiting_give_days)
async def give_days_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    days = parse_int((message.text or "").strip())
    if days is None or days <= 0:
        await message.answer("Количество дней должно быть больше 0.")
        return
    data = await state.get_data()
    await state.clear()
    try:
        await _give_days(session, int(data["telegram_id"]), days)
    except ValueError:
        await message.answer("Пользователь не найден.", reply_markup=keyboards.admin_menu())
        return
    user = await users.get_user_by_telegram_id(session, int(data["telegram_id"]))
    await logs.admin_log(
        session,
        admin_id=message.from_user.id,
        action="access_granted",
        target_user_id=int(data["telegram_id"]),
        details={"days": days},
    )
    await message.answer(f"Готово. Доступ до: <b>{format_date(user)}</b>", reply_markup=keyboards.admin_menu())


@router.message(Command("give"))
async def give_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 3 or parse_int(parts[1]) is None or parse_int(parts[2]) is None:
        await message.answer("Формат: <code>/give telegram_id days</code>")
        return
    try:
        await _give_days(session, int(parts[1]), int(parts[2]))
    except ValueError:
        await message.answer("Пользователь не найден.")
        return
    user = await users.get_user_by_telegram_id(session, int(parts[1]))
    await logs.admin_log(
        session,
        admin_id=message.from_user.id,
        action="access_granted",
        target_user_id=int(parts[1]),
        details={"days": int(parts[2])},
    )
    await message.answer(f"Готово. Доступ до: <b>{format_date(user)}</b>")


async def _give_days(session: AsyncSession, telegram_id: int, days: int) -> None:
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        raise ValueError("User not found")
    settings = get_settings()
    subscriptions.extend_subscription(user, days)
    user.bonus_days += days
    await subscriptions.sync_vpn_access(user, get_vpn_provider(settings))


@router.callback_query(F.data == "admin:disable")
async def disable_start(callback: CallbackQuery, state: FSMContext) -> None:
    if not await require_admin_callback(callback):
        return
    await state.set_state(AdminUserFlow.waiting_disable_user_id)
    await callback.message.edit_text("<b>🚫 Отключить доступ</b>\n\nВведи Telegram ID:")
    await callback.answer()


@router.message(AdminUserFlow.waiting_disable_user_id)
async def disable_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    if not await require_admin_message(message):
        return
    telegram_id = parse_int((message.text or "").strip())
    if telegram_id is None:
        await message.answer("Telegram ID должен быть числом.")
        return
    await state.clear()
    ok = await _disable_user(session, telegram_id)
    if ok:
        await logs.admin_log(session, admin_id=message.from_user.id, action="access_disabled", target_user_id=telegram_id)
    text = "Доступ отключён." if ok else "Пользователь не найден."
    await message.answer(text, reply_markup=keyboards.admin_menu())


@router.message(Command("disable"))
async def disable_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2 or parse_int(parts[1]) is None:
        await message.answer("Формат: <code>/disable telegram_id</code>")
        return
    ok = await _disable_user(session, int(parts[1]))
    if ok:
        await logs.admin_log(session, admin_id=message.from_user.id, action="access_disabled", target_user_id=int(parts[1]))
    await message.answer("Доступ отключён." if ok else "Пользователь не найден.")


async def _disable_user(session: AsyncSession, telegram_id: int) -> bool:
    user = await users.get_user_by_telegram_id(session, telegram_id)
    if not user:
        return False
    settings = get_settings()
    await subscriptions.disable_access(user, get_vpn_provider(settings))
    return True


@router.message(Command("promo"))
async def promo_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) not in (3, 4):
        await message.answer("Формат: <code>/promo code discount_percent max_uses</code>")
        return
    code = parts[1].strip().upper()
    discount = parse_int(parts[2])
    limit = parse_int(parts[3]) if len(parts) == 4 and parts[3] != "-" else None
    if discount is None or discount <= 0 or discount >= 100:
        await message.answer("Скидка должна быть числом от 1 до 99.")
        return
    result = await session.execute(select(PromoCode).where(func.upper(PromoCode.code) == code))
    promo = result.scalar_one_or_none()
    if promo is None:
        promo = PromoCode(code=code, discount_percent=discount, first_payment_only=True)
        session.add(promo)
    promo.discount_percent = discount
    promo.max_uses = limit
    promo.first_payment_only = True
    promo.is_active = True
    await logs.admin_log(
        session,
        admin_id=message.from_user.id,
        action="promo_created",
        details={"code": code, "discount": discount, "limit": limit},
    )
    await message.answer(f"Промокод <code>{html.escape(code)}</code> сохранён.")


@router.message(Command("promo_off"))
async def promo_off_command(message: Message, session: AsyncSession) -> None:
    if not await require_admin_message(message):
        return
    parts = (message.text or "").split()
    if len(parts) != 2:
        await message.answer("Формат: <code>/promo_off code</code>")
        return
    code = parts[1].strip().upper()
    result = await session.execute(select(PromoCode).where(func.upper(PromoCode.code) == code))
    promo = result.scalar_one_or_none()
    if not promo:
        await message.answer("Промокод не найден.")
        return
    promo.is_active = False
    await logs.admin_log(
        session,
        admin_id=message.from_user.id,
        action="promo_disabled",
        details={"code": promo.code},
    )
    await message.answer(f"Промокод <code>{html.escape(promo.code)}</code> отключён.")


@router.message(Command("broadcast"))
async def broadcast_command(message: Message, session: AsyncSession, bot: Bot) -> None:
    if not await require_admin_message(message):
        return
    text = (message.text or "").removeprefix("/broadcast").strip()
    if not text:
        await message.answer("Формат: <code>/broadcast text</code>")
        return
    recipients = await _broadcast_recipients(session, "all")
    sent = 0
    for telegram_id in recipients:
        try:
            await bot.send_message(telegram_id, text, parse_mode=None)
            sent += 1
        except Exception:
            continue
    await logs.admin_log(
        session,
        admin_id=message.from_user.id,
        action="broadcast_sent",
        details={"segment": "all", "sent": sent},
    )
    await message.answer(f"Отправлено: <b>{sent}</b>")
