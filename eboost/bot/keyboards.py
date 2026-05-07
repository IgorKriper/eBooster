from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from eboost.models import Payment, Plan, User


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Попробовать бесплатно", callback_data="trial")],
            [InlineKeyboardButton(text="⚡ Доступ", callback_data="access")],
            [InlineKeyboardButton(text="👤 Кабинет", callback_data="cabinet")],
            [InlineKeyboardButton(text="ℹ️ Инфо", callback_data="info")],
        ]
    )


def back_menu(target: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад", callback_data=target)]])


def plans_menu(plans: list[Plan]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{plan.title} - {plan.price_rub}₽", callback_data=f"plan:{plan.id}")]
        for plan in plans
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


def connect_menu(user: User) -> InlineKeyboardMarkup:
    url = user.vpn_subscription_url or "https://example.com"
    if "mock-vpn.eboost.local" in url:
        connect_button = InlineKeyboardButton(text="Подключить eBoost", callback_data="mock_connect")
    else:
        connect_button = InlineKeyboardButton(text="Подключить eBoost", url=url)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [connect_button],
            [
                InlineKeyboardButton(text="iPhone", callback_data="device:iphone"),
                InlineKeyboardButton(text="Android", callback_data="device:android"),
            ],
            [
                InlineKeyboardButton(text="Windows", callback_data="device:windows"),
                InlineKeyboardButton(text="Mac", callback_data="device:mac"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def cabinet_menu(user: User) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Пригласить друга", callback_data="invite")],
            [InlineKeyboardButton(text="История оплат", callback_data="payments_history")],
            [InlineKeyboardButton(text="Подключить eBoost", callback_data="connect")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def info_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Документы", callback_data="documents")],
            [InlineKeyboardButton(text="Инструкции", callback_data="connect")],
            [InlineKeyboardButton(text="Поддержка", callback_data="support")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def documents_menu(slugs: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=title, callback_data=f"doc:{slug}")] for slug, title in slugs]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="info")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
