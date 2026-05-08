from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from eboost.models import Payment, Plan


def plans_menu(plans: list[Plan], back_to: str = "main") -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=f"{plan.title} - {plan.price_rub}₽", callback_data=f"plan:{plan.id}")]
        for plan in plans
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def active_access_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📲 Открыть подключение", callback_data="connect")],
            [InlineKeyboardButton(text="💳 Продлить доступ", callback_data="access_extend")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="main")],
        ]
    )


def promo_question_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Перейти к оплате", callback_data="pay_without_promo")],
            [InlineKeyboardButton(text="🎟 Ввести промокод", callback_data="promo_enter")],
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
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="access")],
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
            [InlineKeyboardButton(text="🔄 Проверить оплату", callback_data=f"payment_check:{payment.id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="access")],
        ]
    )


def after_payment_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📲 Открыть подключение", callback_data="connect")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="main")],
        ]
    )
