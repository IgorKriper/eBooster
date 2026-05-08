from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def trial_offer_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Активировать доступ", callback_data="trial_activate")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def trial_already_used_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Выбрать тариф", callback_data="access")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )
