from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from eboost.core.time import as_utc, utcnow
from eboost.models import NotificationLog, Payment, User
from eboost.models.notification import NotificationType
from eboost.models.payment import PaymentStatus
from eboost.services import logs, subscriptions
from eboost.services.vpn.base import VpnProvider

logger = logging.getLogger(__name__)

CHECK_INTERVAL_SECONDS = 60 * 5


async def notification_loop(bot: Bot, session_maker: async_sessionmaker[AsyncSession]) -> None:
    while True:
        try:
            async with session_maker() as session:
                from eboost.core.config import get_settings
                from eboost.services.vpn.factory import get_vpn_provider

                settings = get_settings()
                await send_scheduled_notifications(bot, session, vpn_provider=get_vpn_provider(settings))
                await session.commit()
        except Exception:
            logger.exception("Notification loop failed")
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


async def send_scheduled_notifications(bot: Bot, session: AsyncSession, *, vpn_provider: VpnProvider | None = None) -> int:
    now = utcnow()
    result = await session.execute(select(User).where(User.is_disabled.is_(False)))
    sent = 0
    for user in result.scalars().all():
        payment_count = await _successful_payment_count(session, user.id)
        notification_type = _next_notification_type(user, now=now, payment_count=payment_count)
        if notification_type is None:
            continue
        if await _already_sent(session, user_id=user.id, notification_type=notification_type):
            continue
        try:
            await bot.send_message(
                user.telegram_id,
                _message_for(notification_type),
                reply_markup=_keyboard_for(notification_type),
            )
        except Exception:
            logger.exception("Could not send notification to user %s", user.telegram_id)
            continue
        session.add(NotificationLog(user_id=user.id, type=notification_type))
        if notification_type in {NotificationType.TRIAL_EXPIRED, NotificationType.SUB_EXPIRED} and vpn_provider:
            try:
                await subscriptions.disable_access(user, vpn_provider)
                await logs.system_log(session, event="access_expired", user_id=user.id, details={"type": notification_type})
                await logs.system_log(session, event="vpn_disabled", user_id=user.id, details={"vpn_user_id": user.vpn_user_id})
            except Exception as exc:
                await logs.system_log(session, event="vpn_error", user_id=user.id, details={"error": str(exc)})
        sent += 1
    return sent


async def _successful_payment_count(session: AsyncSession, user_id: int) -> int:
    result = await session.execute(
        select(func.count(Payment.id)).where(Payment.user_id == user_id, Payment.status == PaymentStatus.SUCCEEDED)
    )
    return int(result.scalar_one())


def _next_notification_type(user: User, *, now, payment_count: int) -> str | None:
    created_at = as_utc(user.created_at)
    trial_started_at = as_utc(user.trial_started_at)
    subscription_until = as_utc(user.subscription_until)
    connected_at = as_utc(user.connected_at)

    if payment_count > 0:
        if subscription_until is None:
            return None
        left = subscription_until - now
        if left.total_seconds() <= 0:
            return NotificationType.SUB_EXPIRED
        if left <= timedelta(days=1):
            return NotificationType.SUB_EXPIRE_1D
        if left <= timedelta(days=3):
            return NotificationType.SUB_EXPIRE_3D
        return None

    if trial_started_at is None:
        if created_at is None:
            return None
        age = now - created_at
        if age >= timedelta(hours=24):
            return NotificationType.START_NO_TRIAL_24H
        if age >= timedelta(hours=1):
            return NotificationType.START_NO_TRIAL_1H
        return None

    if subscription_until is None:
        return None
    left = subscription_until - now
    if left.total_seconds() <= 0:
        return NotificationType.TRIAL_EXPIRED
    if left <= timedelta(days=1):
        return NotificationType.TRIAL_EXPIRE_24H
    if connected_at and now - connected_at >= timedelta(hours=24):
        return NotificationType.CONNECTED_24H
    return None


async def _already_sent(session: AsyncSession, *, user_id: int, notification_type: str) -> bool:
    result = await session.execute(
        select(NotificationLog).where(NotificationLog.user_id == user_id, NotificationLog.type == notification_type)
    )
    return result.scalar_one_or_none() is not None


def _message_for(notification_type: str) -> str:
    messages = {
        NotificationType.START_NO_TRIAL_1H: (
            "<b>🚀 Ты ещё не подключил eBooster</b>\n\n"
            "Попробуй бесплатно - подключение занимает меньше минуты"
        ),
        NotificationType.START_NO_TRIAL_24H: (
            "<b>🎁 Бесплатный доступ всё ещё доступен</b>\n\n"
            "У тебя есть 3 дня, чтобы попробовать eBooster"
        ),
        NotificationType.CONNECTED_24H: (
            "<b>🚀 Как работает eBooster?</b>\n\n"
            "Ты уже попробовал eBooster в работе.\n\n"
            "Соединение стало стабильнее в повседневных задачах\n"
            "и интернет работает без лишних задержек.\n\n"
            "Если всё устраивает - можно продолжить пользоваться\n"
            "и продлить доступ."
        ),
        NotificationType.TRIAL_EXPIRE_24H: (
            "<b>⏳ Пробный доступ скоро закончится</b>\n\n"
            "Остался 1 день бесплатного доступа"
        ),
        NotificationType.TRIAL_EXPIRED: (
            "<b>⛔ Доступ закончился</b>\n\n"
            "Чтобы продолжить пользоваться eBooster - выбери тариф"
        ),
        NotificationType.SUB_EXPIRE_3D: "<b>⏳ Доступ скоро закончится</b>",
        NotificationType.SUB_EXPIRE_1D: "<b>⚠️ Остался 1 день</b>",
        NotificationType.SUB_EXPIRED: "<b>⛔ Доступ закончился</b>",
    }
    return messages[notification_type]


def _keyboard_for(notification_type: str) -> InlineKeyboardMarkup:
    if notification_type == NotificationType.CONNECTED_24H:
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="⚡ Продлить доступ", callback_data="access_extend")],
                [InlineKeyboardButton(text="⬅️ В меню", callback_data="main")],
            ]
        )
    if notification_type == NotificationType.START_NO_TRIAL_1H:
        text = "🎁 Попробовать бесплатно"
        callback_data = "trial"
    elif notification_type == NotificationType.START_NO_TRIAL_24H:
        text = "🚀 Активировать доступ"
        callback_data = "trial_activate"
    elif notification_type == NotificationType.TRIAL_EXPIRED:
        text = "⚡ Получить доступ"
        callback_data = "access"
    elif notification_type == NotificationType.TRIAL_EXPIRE_24H:
        text = "⚡ Выбрать тариф"
        callback_data = "access"
    elif notification_type == NotificationType.SUB_EXPIRED:
        text = "⚡ Выбрать тариф"
        callback_data = "access"
    else:
        text = "💳 Продлить доступ"
        callback_data = "access"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]])
