def plans() -> str:
    return (
        "<b>⚡ Доступ к eBoost</b>\n\n"
        "Выбери тариф:\n\n"
        "<b>1 месяц</b> - 299₽\n"
        "<b>3 месяца</b> - 799₽\n"
        "<b>12 месяцев</b> - 1990₽\n\n"
        "Чем дольше срок - тем выгоднее подключение."
    )


def selected_plan(title: str, price: int, duration_days: int) -> str:
    if duration_days <= 31:
        note = "Если планируешь пользоваться регулярно - выгоднее выбрать тариф на несколько месяцев."
    elif duration_days <= 100:
        note = "Хороший выбор: выгоднее, чем продлевать каждый месяц."
    else:
        note = "Отличный выбор: максимальная выгода и стабильный доступ."

    return (
        "<b>⚡ Тариф выбран</b>\n\n"
        f"{title.replace('eBoost на ', 'eBoost на <b>')}</b>\n"
        f"Стоимость: <b>{price}₽</b>\n\n"
        f"{note}\n\n"
        "Промокод можно применить при первой оплате."
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


def active_until(date: str) -> str:
    return (
        "<b>✅ Доступ активен</b>\n\n"
        f"До: <b>{date}</b>"
    )
