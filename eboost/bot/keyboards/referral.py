from __future__ import annotations

from urllib.parse import quote

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def referral_menu(referral_link: str) -> InlineKeyboardMarkup:
    share_url = f"https://t.me/share/url?url={quote(referral_link)}&text={quote('Попробуй eBooster')}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=share_url)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cabinet")],
        ]
    )
