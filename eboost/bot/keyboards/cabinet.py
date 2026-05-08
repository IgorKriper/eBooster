from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cabinet_menu(*, has_active: bool = True) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if has_active:
        rows.append([InlineKeyboardButton(text="🚀 Открыть и подключить", callback_data="connect")])
        rows.append([InlineKeyboardButton(text="➕ Добавить устройство", callback_data="device_pack")])
        rows.append([InlineKeyboardButton(text="⚡ Продлить", callback_data="access_extend")])
    else:
        rows.append([InlineKeyboardButton(text="⚡ Получить доступ", callback_data="access")])
    rows.append([InlineKeyboardButton(text="🎁 Пригласить друга", callback_data="invite")])
    rows.append([InlineKeyboardButton(text="🧾 История оплат", callback_data="payments_history")])
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def cabinet_no_access_menu() -> InlineKeyboardMarkup:
    return cabinet_menu(has_active=False)


def payment_history_empty_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Выбрать тариф", callback_data="access")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="cabinet")],
        ]
    )
