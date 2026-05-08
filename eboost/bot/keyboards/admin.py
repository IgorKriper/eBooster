from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def admin_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="🌍 Серверы", callback_data="admin:servers")],
            [InlineKeyboardButton(text="🎟 Промокоды", callback_data="admin:promos")],
            [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin:broadcast")],
            [InlineKeyboardButton(text="👤 Пользователь", callback_data="admin:user")],
            [InlineKeyboardButton(text="⚙️ Выдать доступ", callback_data="admin:give")],
            [InlineKeyboardButton(text="🚫 Отключить доступ", callback_data="admin:disable")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def admin_servers_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Нагрузка серверов", callback_data="admin:servers_load")],
            [InlineKeyboardButton(text="🚫 Отключить сервер", callback_data="admin:servers_disable")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")],
        ]
    )


def admin_server_toggle_menu(servers: list[tuple[str, str, bool]]) -> InlineKeyboardMarkup:
    rows = []
    for code, name, is_enabled in servers:
        action = "disable" if is_enabled else "enable"
        prefix = "✅" if is_enabled else "🚫"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{prefix} {name}",
                    callback_data=f"admin:server_toggle:{code}:{action}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:servers")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_promos_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin:promo_create")],
            [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin:promo_list")],
            [InlineKeyboardButton(text="❌ Отключить промокод", callback_data="admin:promo_disable")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")],
        ]
    )


def admin_broadcast_segments_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Всем пользователям", callback_data="admin:broadcast_segment:all")],
            [InlineKeyboardButton(text="Start без пробника", callback_data="admin:broadcast_segment:no_trial")],
            [InlineKeyboardButton(text="Пробник без оплаты", callback_data="admin:broadcast_segment:trial_no_payment")],
            [InlineKeyboardButton(text="Истёкший доступ", callback_data="admin:broadcast_segment:expired")],
            [InlineKeyboardButton(text="Активные подписчики", callback_data="admin:broadcast_segment:active_paid")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="admin")],
        ]
    )


def admin_broadcast_confirm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Отправить", callback_data="admin:broadcast_send")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="admin:broadcast_cancel")],
        ]
    )
