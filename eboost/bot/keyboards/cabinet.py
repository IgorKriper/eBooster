from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cabinet_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📲 Открыть подключение", callback_data="connect")],
            [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="invite")],
            [InlineKeyboardButton(text="💳 История оплат", callback_data="payments_history")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def cabinet_no_access_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Получить доступ", callback_data="access")],
            [InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="invite")],
            [InlineKeyboardButton(text="💳 История оплат", callback_data="payments_history")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def payment_history_empty_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Выбрать тариф", callback_data="access")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cabinet")],
        ]
    )
