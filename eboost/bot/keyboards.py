from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from eboost.models import Payment, Plan, User
from eboost.services.subscriptions import is_subscription_active


def main_menu(user: User | None = None) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if user is not None and is_subscription_active(user):
        rows.append(
            [InlineKeyboardButton(text="🚀 Открыть и подключить", callback_data="connect")]
        )
        rows.append(
            [InlineKeyboardButton(text="➕ Добавить устройство", callback_data="add_device")]
        )
        rows.append([InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="access")])
    else:
        rows.append(
            [InlineKeyboardButton(text="🚀 Активировать пробный период", callback_data="trial")]
        )
        rows.append([InlineKeyboardButton(text="⚡ Тарифы", callback_data="access")])
    rows.append([InlineKeyboardButton(text="👤 Кабинет", callback_data="cabinet")])
    rows.append([InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def trial_cta_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Активировать пробный период", callback_data="trial")],
            [InlineKeyboardButton(text="⚡ Посмотреть тарифы", callback_data="access")],
            [InlineKeyboardButton(text="ℹ️ Подробнее об eBooster", callback_data="info")],
        ]
    )


def back_menu(target: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=target)]]
    )


def plans_menu(plans: list[Plan]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{plan.title} — {plan.price_rub}₽",
                callback_data=f"plan:{plan.id}",
            )
        ]
        for plan in plans
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def device_packs_menu(packs: list[Plan]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                text=f"{pack.title} — {pack.price_rub}₽",
                callback_data=f"plan:{pack.id}",
            )
        ]
        for pack in packs
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="main")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def promo_question_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="promo_enter")],
            [InlineKeyboardButton(text="💳 Перейти к оплате", callback_data="pay_without_promo")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="access")],
        ]
    )


def promo_applied_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить со скидкой", callback_data="pay_with_promo")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="access")],
        ]
    )


def promo_invalid_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎟 Ввести другой", callback_data="promo_enter")],
            [InlineKeyboardButton(text="💳 Оплатить без скидки", callback_data="pay_without_promo")],
        ]
    )


def payment_menu(payment: Payment) -> InlineKeyboardMarkup:
    if payment.payment_url and ("localhost" in payment.payment_url or "127.0.0.1" in payment.payment_url):
        pay_button = InlineKeyboardButton(text="💳 Оплатить", callback_data=f"mock_pay:{payment.id}")
    else:
        pay_button = InlineKeyboardButton(text="💳 Оплатить", url=payment.payment_url or "https://example.com")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [pay_button],
            [InlineKeyboardButton(text="Проверить оплату", callback_data=f"payment_check:{payment.id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="access")],
        ]
    )


def connect_open_menu(connect_url: str) -> InlineKeyboardMarkup:
    """Inline keyboard shown after a successful payment / on the active panel.

    The button always points at the branded eBooster connect page; the page in
    turn opens Happ via ``happ://add/...`` so we never publish the raw
    subscription URL into Telegram.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть и подключить", url=connect_url)],
            [InlineKeyboardButton(text="➕ Добавить устройство", callback_data="add_device")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="main")],
        ]
    )


def connect_unavailable_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Активировать пробный период", callback_data="trial")],
            [InlineKeyboardButton(text="💳 Посмотреть тарифы", callback_data="access")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="main")],
        ]
    )


def cabinet_menu(user: User) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="👥 Пригласить друга", callback_data="invite")],
            [InlineKeyboardButton(text="📒 История оплат", callback_data="payments_history")],
            [InlineKeyboardButton(text="🚀 Открыть и подключить", callback_data="connect")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def info_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Документы", callback_data="documents")],
            [InlineKeyboardButton(text="📘 Инструкции", callback_data="connect")],
            [InlineKeyboardButton(text="💬 Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def documents_menu(slugs: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=title, callback_data=f"doc:{slug}")] for slug, title in slugs]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="info")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def admin_root_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin:stats")],
            [InlineKeyboardButton(text="👤 Пользователь", callback_data="admin:user")],
            [InlineKeyboardButton(text="🎁 Выдать дни", callback_data="admin:give")],
            [InlineKeyboardButton(text="🛑 Отключить доступ", callback_data="admin:disable")],
            [InlineKeyboardButton(text="📊 Рефералы", callback_data="admin:referrals")],
            [InlineKeyboardButton(text="📣 Рассылка", callback_data="admin:broadcast")],
        ]
    )


def admin_input_menu(target: str = "admin:menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data=target),
                InlineKeyboardButton(text="❌ Отмена", callback_data="admin:cancel"),
            ]
        ]
    )


def admin_back_menu(target: str = "admin:menu") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=target)]]
    )


def admin_referrers_menu(items: list[tuple[int, str]]) -> InlineKeyboardMarkup:
    """``items`` is a list of ``(referrer_id, label)``."""
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"admin:ref:{ref_id}")]
        for ref_id, label in items
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="admin:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
