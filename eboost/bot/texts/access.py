def plans() -> str:
    return (
        "<b>⚡ Тарифы</b>\n\n"
        "Все тарифы — на 30 дней. Различаются только числом устройств.\n\n"
        "⚡ <b>Solo</b> — 200₽ · 2 устройства\n"
        "🚀 <b>Plus</b> — 349₽ · 5 устройств\n"
        "👑 <b>Family</b> — 590₽ · 10 устройств\n\n"
        "Выбери тариф ниже."
    )


def device_packs(current_limit: int) -> str:
    return (
        "<b>➕ Добавить устройство</b>\n\n"
        f"Сейчас в подписке: <b>{current_limit}</b> устройств.\n\n"
        "Доп. устройство добавится к текущей подписке "
        "и будет действовать до её окончания."
    )


def connect_panel(connect_url: str) -> str:  # noqa: ARG001 — URL отдаётся кнопкой
    return (
        "<b>🚀 Открыть и подключить</b>\n\n"
        "Нажми кнопку ниже — откроется eBooster в приложении Happ.\n"
        "Если Happ ещё не установлен, его можно скачать прямо со страницы."
    )


CONNECT_NO_ACCESS = (
    "<b>⚠️ Подписка не активна</b>\n\n"
    "Активируй пробный доступ или выбери тариф."
)


def selected_plan(title: str, price: int, duration_days: int, devices: int = 0) -> str:
    period = "30 дней" if duration_days == 30 else f"{duration_days} дн."
    devices_line = f"Устройств: <b>{devices}</b>\n" if devices else ""
    return (
        "<b>⚡ Тариф выбран</b>\n\n"
        f"<b>{title}</b>\n"
        f"Период: <b>{period}</b>\n"
        f"{devices_line}"
        f"Стоимость: <b>{price}₽</b>\n\n"
        "Промокод можно применить при первой оплате."
    )


def selected_device_pack(title: str, price: int, addon_devices: int, current_limit: int) -> str:
    return (
        "<b>➕ Доп. устройство</b>\n\n"
        f"<b>{title}</b>\n"
        f"Стоимость: <b>{price}₽</b>\n\n"
        f"После оплаты в подписке будет: <b>{current_limit + max(addon_devices, 0)}</b> устройств."
    )


def promo_applied(title: str, discount: int, total: int) -> str:
    return (
        "<b>🎟 Промокод применён</b>\n\n"
        f"Скидка: <b>{discount}%</b>\n"
        f"Итого: <b>{total}₽</b>"
    )


PROMO_ENTER = "<b>🎟 Промокод</b>\n\nВведи промокод одним сообщением:"

RECEIPT_EMAIL_ENTER = (
    "<b>📩 Email для чека</b>\n\n"
    "ЮKassa требует отправить чек после оплаты.\n"
    "Введи email одним сообщением:"
)

RECEIPT_EMAIL_INVALID = (
    "<b>⚠️ Email не похож на правильный</b>\n\n"
    "Проверь адрес и отправь ещё раз."
)

PROMO_INVALID = (
    "<b>⚠️ Промокод не найден</b>\n\n"
    "Проверь код или перейди к оплате без скидки."
)


def payment_created(title: str, amount: int) -> str:
    return (
        "<b>💳 Счёт создан</b>\n\n"
        f"Тариф: <b>{title}</b>\n"
        f"К оплате: <b>{amount}₽</b>\n\n"
        "Открой ссылку для оплаты.\n"
        "После оплаты доступ откроется автоматически."
    )


PAYMENT_UNAVAILABLE = (
    "<b>⚠️ Оплата временно недоступна</b>\n\n"
    "Попробуй позже или напиши в поддержку."
)


PAYMENT_SUCCESS = (
    "<b>✅ Доступ открыт</b>"
)


def active_until(date: str, devices: int | None = None) -> str:
    """S08 — мой доступ (активный).

    Показывает дату окончания и лимит устройств, если известен.
    """
    devices_line = f"Лимит устройств: <b>{devices}</b>\n" if devices else ""
    return (
        "<b>✅ Доступ активен</b>\n\n"
        f"До: <b>{date}</b>\n"
        f"{devices_line}"
    )
