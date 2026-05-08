from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from eboost.core.config import get_settings
from eboost.models import User
from eboost.services.subscriptions import is_subscription_active


def main_menu(user: User | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if user and is_subscription_active(user):
        rows.append([InlineKeyboardButton(text="🚀 Открыть и подключить", callback_data="connect")])
        rows.append([InlineKeyboardButton(text="➕ Добавить устройство", callback_data="device_pack")])
        rows.append([InlineKeyboardButton(text="⚡ Продлить", callback_data="access_extend")])
    elif user and user.trial_started_at:
        rows.append([InlineKeyboardButton(text="⚡ Выбрать тариф", callback_data="access")])
        rows.append([InlineKeyboardButton(text="🎁 Реферальная программа", callback_data="invite")])
    else:
        rows.append([InlineKeyboardButton(text="🚀 Активировать пробный период", callback_data="trial")])
        rows.append([InlineKeyboardButton(text="⚡ Тарифы", callback_data="access")])

    rows.append([InlineKeyboardButton(text="👤 Кабинет", callback_data="cabinet")])
    rows.append([InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")])
    if user and user.telegram_id in get_settings().admin_id_set:
        rows.append([InlineKeyboardButton(text="🛠 Админ", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
