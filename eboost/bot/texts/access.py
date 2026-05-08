from __future__ import annotations

from eboost.models import Plan
from eboost.services.plans import (
    TARIFF_EMOJIS,
    TARIFF_SLOT_LIMITS,
    TARIFF_TAGLINES,
    TARIFF_TITLES,
    period_label,
)


# ---------- Top-level / overview screens ---------------------------------- #

def plans() -> str:
    """Tariff overview (S05 in TZ)."""
    return (
        "<b>⚡ Тарифы eBooster</b>\n\n"
        "Выбери, сколько устройств подключить:\n\n"
        "💎 <b>Solo</b> · 2 устройства — для одного человека\n"
        "🚀 <b>Plus</b> · 5 устройств — для всех своих устройств\n"
        "👑 <b>Family</b> · 10 устройств — для семьи и друзей\n\n"
        "Дальше выберешь срок: 1 / 3 / 12 месяцев."
    )


def selected_tariff(tariff_code: str, slot_limit: int) -> str:
    """Period picker header (S05a)."""
    emoji = TARIFF_EMOJIS.get(tariff_code, "⚡")
    title = TARIFF_TITLES.get(tariff_code, tariff_code.title())
    tagline = TARIFF_TAGLINES.get(tariff_code, "")
    tagline_line = f"\n{tagline}" if tagline else ""
    return (
        f"<b>{emoji} {title}</b> · {slot_limit} устройств{tagline_line}\n\n"
        "Выбери срок подписки:"
    )


# ---------- Plan / device-pack confirmation ------------------------------- #

def selected_plan(plan: Plan) -> str:
    """S06 — confirmation card before paying for a subscription tariff."""
    tariff_code = plan.tariff_code or ""
    emoji = TARIFF_EMOJIS.get(tariff_code, "⚡")
    title = TARIFF_TITLES.get(tariff_code, plan.title)
    slot_limit = TARIFF_SLOT_LIMITS.get(tariff_code, int(plan.slot_limit or 0))
    period = period_label(plan.period_months)
    period_line = f"Срок: <b>{period}</b>\n" if period else ""
    slot_line = f"Устройств: <b>{slot_limit}</b>\n" if slot_limit else ""
    return (
        f"<b>{emoji} {title}</b>\n\n"
        f"{period_line}"
        f"{slot_line}"
        f"Сумма: <b>{plan.price_rub}₽</b>"
    )


def selected_device_pack(plan: Plan) -> str:
    bonus = int(plan.bonus_devices or 0)
    return (
        "<b>➕ Дополнительное устройство</b>\n\n"
        f"{plan.title}\n"
        f"К текущему тарифу: <b>+{bonus} слот{('а' if 1 < bonus < 5 else '' if bonus == 1 else 'ов')}</b>\n"
        f"Сумма: <b>{plan.price_rub}₽</b>"
    )


# ---------- Active subscription / payment screens ------------------------- #

def active_until(date: str) -> str:
    return (
        "<b>⚡ Тариф eBooster активен</b>\n\n"
        f"Доступ до: <b>{date}</b>\n\n"
        "Можно подключаться, добавлять устройства или продлить тариф."
    )


def device_packs(current_limit: int = 0) -> str:
    base = (
        "<b>➕ Дополнительные устройства</b>\n\n"
        "Solo рассчитан на 2 устройства. Можно добавить ещё слоты "
        "под одну подписку.\n\n"
        "Если устройств нужно больше 2-х суммарно — выгоднее перейти "
        "на Plus или Family."
    )
    if current_limit:
        return base + f"\n\nСейчас доступно слотов: <b>{current_limit}</b>"
    return base


# ---------- Promo / payment flow constants ------------------------------- #

PROMO_QUESTION = "🎟 У тебя есть промокод?"
PROMO_ENTER = "🎟 Введи промокод сообщением:"
PROMO_INVALID = "🎟 Промокод не подходит. Можно ввести другой или оплатить без скидки."
PAYMENT_UNAVAILABLE = "⚠️ Оплата временно недоступна. Попробуй позже."
PAYMENT_SUCCESS = "✅ Оплата прошла. Можно подключаться."
RECEIPT_EMAIL_INVALID = "📧 Не похоже на email. Введи адрес для отправки чека."
RECEIPT_EMAIL_REQUEST = "📧 Введи email для отправки чека (нужен по 54-ФЗ)."


def promo_applied(plan_title: str, discount_percent: int, final_amount: int) -> str:
    return (
        "<b>🎟 Промокод применён</b>\n\n"
        f"Тариф: <b>{plan_title}</b>\n"
        f"Скидка: <b>-{discount_percent}%</b>\n"
        f"К оплате: <b>{final_amount}₽</b>"
    )


def payment_created(plan_title: str, final_amount: int) -> str:
    return (
        "<b>💳 Оплата</b>\n\n"
        f"Тариф: <b>{plan_title}</b>\n"
        f"К оплате: <b>{final_amount}₽</b>\n\n"
        "После оплаты вернись и нажми «🔄 Проверить оплату»."
    )


def connect_panel(public_url: str) -> str:
    """S10 — single-shot subscription URL panel.

    Note: `public_url` intentionally not echoed back into the body — кнопка
    «Открыть и подключить» сама несёт ссылку. Текст остаётся коротким, чтобы
    карточка хорошо смотрелась.
    """
    del public_url  # used only by the keyboard
    return (
        "<b>🚀 Подключение готово</b>\n\n"
        "Нажми «🚀 Открыть и подключить» — Happ откроется и подхватит твой "
        "профиль автоматически.\n\n"
        "Если автозапуск не сработал — открой инструкцию для своей платформы."
    )


__all__ = [
    "PAYMENT_SUCCESS",
    "PAYMENT_UNAVAILABLE",
    "PROMO_ENTER",
    "PROMO_INVALID",
    "PROMO_QUESTION",
    "RECEIPT_EMAIL_INVALID",
    "RECEIPT_EMAIL_REQUEST",
    "active_until",
    "connect_panel",
    "device_packs",
    "payment_created",
    "plans",
    "promo_applied",
    "selected_device_pack",
    "selected_plan",
    "selected_tariff",
]
