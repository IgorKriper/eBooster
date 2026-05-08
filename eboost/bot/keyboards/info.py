from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def info_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📄 Документы", callback_data="documents"),
                InlineKeyboardButton(text="🆘 Поддержка", callback_data="support"),
            ],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data="info_instruction")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def support_menu(support_username: str) -> InlineKeyboardMarkup:
    username = support_username.removeprefix("@")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Написать в поддержку", url=f"https://t.me/{username}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="info")],
        ]
    )
