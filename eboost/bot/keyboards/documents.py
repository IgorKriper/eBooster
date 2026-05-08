from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


DOC_BUTTONS = {
    "privacy": "🔐 Политика конфиденциальности",
    "terms": "📄 Пользовательское соглашение",
    "refunds": "💸 Политика возвратов",
    "liability": "⚠️ Ограничение ответственности",
}


def documents_menu(slugs: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=DOC_BUTTONS.get(slug, title), callback_data=f"doc:{slug}")]
        for slug, title in slugs
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="info")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
