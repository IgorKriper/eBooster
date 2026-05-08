from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from eboost.models import Payment, Plan
from eboost.services.plans import (
    PERIOD_LABELS,
    PERIOD_ORDER,
    PERIOD_SHORT_LABELS,
    TARIFF_EMOJIS,
    TARIFF_ORDER,
    TARIFF_TITLES,
)


def _device_pack_button(plan: Plan) -> str:
    bonus = int(plan.bonus_devices or 0)
    suffix = f" · +{bonus} уст." if bonus else ""
    return f"➕ {plan.title} · {plan.price_rub}₽{suffix}"


def plans_menu(plans: list[Plan], back_to: str = "main") -> InlineKeyboardMarkup:
    """Used for device-pack add-ons; subscription tariffs use tariff_menu."""
    rows = [
        [InlineKeyboardButton(text=_device_pack_button(plan), callback_data=f"plan:{plan.id}")]
        for plan in plans
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def tariff_menu(
    tariff_min_prices: list[tuple[str, int, int]],
    *,
    back_to: str = "main",
) -> InlineKeyboardMarkup:
    """Top-level tariff picker.

    `tariff_min_prices` is a list of (tariff_code, slot_limit, min_price_rub)
    tuples — minimum price across the tariff's periods (1m).
    """
    items = sorted(
        tariff_min_prices,
        key=lambda item: TARIFF_ORDER.get(item[0], 99),
    )
    rows = []
    for code, slot_limit, min_price in items:
        emoji = TARIFF_EMOJIS.get(code, "⚡")
        title = TARIFF_TITLES.get(code, code.title())
        text = f"{emoji} {title} · {slot_limit} уст. · от {min_price}₽"
        rows.append(
            [InlineKeyboardButton(text=text, callback_data=f"tariff:{code}")]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def period_menu(plans: list[Plan], *, back_to: str = "access") -> InlineKeyboardMarkup:
    """Period picker for one tariff. Plans must already be filtered by tariff_code."""
    plans = sorted(
        plans,
        key=lambda p: PERIOD_ORDER.get(int(p.period_months or 0), 99),
    )
    rows = []
    for plan in plans:
        period = int(plan.period_months or 0)
        label = PERIOD_LABELS.get(period, plan.title)
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{label} — {plan.price_rub}₽",
                    callback_data=f"plan:{plan.id}",
                )
            ]
        )
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def active_access_menu() -> InlineKeyboardMarkup:
    """Cabinet/active access screen (S08): connect, +1 device, extend, back."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть и подключить", callback_data="connect")],
            [InlineKeyboardButton(text="➕ Добавить устройство", callback_data="device_pack")],
            [InlineKeyboardButton(text="⚡ Продлить", callback_data="access_extend")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="main")],
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
            [InlineKeyboardButton(text="🚀 Открыть и подключить", callback_data="connect")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="main")],
        ]
    )


__all__ = [
    "active_access_menu",
    "after_payment_menu",
    "payment_menu",
    "period_menu",
    "plans_menu",
    "promo_applied_menu",
    "promo_invalid_menu",
    "promo_question_menu",
    "tariff_menu",
    "PERIOD_SHORT_LABELS",
]
