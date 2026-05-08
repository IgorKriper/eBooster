from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from eboost.core.config import get_settings
from eboost.models import User
from eboost.services.subscriptions import is_subscription_active


def main_menu(user: User | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if user and is_subscription_active(user):
        rows.append([InlineKeyboardButton(text="⚡ Доступ", callback_data="access")])
    elif user and user.trial_started_at:
        rows.append([InlineKeyboardButton(text="⚡ Получить доступ", callback_data="access")])
    else:
        rows.append([InlineKeyboardButton(text="🚀 Попробовать бесплатно", callback_data="trial")])
        rows.append([InlineKeyboardButton(text="⚡ Доступ", callback_data="access")])

    rows.append([InlineKeyboardButton(text="👤 Кабинет", callback_data="cabinet")])
    rows.append([InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")])
    if user and user.telegram_id in get_settings().admin_id_set:
        rows.append([InlineKeyboardButton(text="🛠 Админ", callback_data="admin")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
