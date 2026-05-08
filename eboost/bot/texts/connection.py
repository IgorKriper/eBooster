DEVICE_SELECT = "<b>📲 Выбери устройство</b>"

INSTRUCTION_SELECT = "<b>📖 Инструкция</b>\n\nВыбери устройство:"

CONNECT = "<b>Подключение eBooster</b>"

READY = (
    "<b>Ускорение включено</b>\n\n"
    "Работает в фоне\n"
    "Можно пользоваться"
)

NO_ACCESS = (
    "<b>⚠️ Доступ не активен</b>\n\n"
    "Активируй пробный доступ или выбери тариф."
)


# Платформенные карточки S11–S14: 4 коротких шага + 4 кнопки.
DEVICE_TITLES: dict[str, str] = {
    "iphone": "📱 iPhone / iPad",
    "android": "🤖 Android",
    "windows": "💻 Windows",
    "mac": "🍏 Mac",
}


CARDS: dict[str, str] = {
    "iphone": (
        "<b>📱 iPhone / iPad — подключение</b>\n\n"
        "1. Скачай <b>Happ</b> из App Store\n"
        "2. Вернись сюда и нажми <b>«🚀 Открыть и подключить»</b>\n"
        "3. Подтверди добавление профиля и разреши VPN в настройках iOS\n"
        "4. Включи eBooster в Happ\n\n"
        "Если не сработало — скопируй ссылку и добавь подключение в Happ вручную."
    ),
    "android": (
        "<b>🤖 Android — подключение</b>\n\n"
        "1. Скачай <b>Happ</b> из Google Play\n"
        "2. Вернись сюда и нажми <b>«🚀 Открыть и подключить»</b>\n"
        "3. Подтверди добавление подключения в Happ\n"
        "4. Включи eBooster в приложении\n\n"
        "Если не сработало — скопируй ссылку и добавь подключение в Happ вручную."
    ),
    "windows": (
        "<b>💻 Windows — подключение</b>\n\n"
        "1. Скачай и установи <b>Happ</b> для Windows\n"
        "2. Скопируй ссылку кнопкой ниже\n"
        "3. Открой Happ → добавь подключение → вставь ссылку\n"
        "4. Включи eBooster в приложении"
    ),
    "mac": (
        "<b>🍏 Mac — подключение</b>\n\n"
        "1. Скачай и установи <b>Happ</b> для macOS\n"
        "2. Скопируй ссылку кнопкой ниже\n"
        "3. Открой Happ → добавь подключение → вставь ссылку\n"
        "4. Включи eBooster в приложении"
    ),
}


# Legacy alias so existing imports don't break.
INSTRUCTIONS = CARDS


def copy_link(url: str) -> str:  # noqa: ARG001 — link sent via separate message
    return (
        "<b>Не получилось автоматически</b>\n\n"
        "1. Скопируй ссылку\n"
        "2. Открой Happ\n"
        "3. Добавь подключение"
    )


def copy_link_message(url: str) -> str:
    """Sent in chat when CopyTextButton can't fit the link (>256 bytes)."""
    return (
        "<b>📋 Ссылка eBooster</b>\n"
        "Скопируй и вставь её в Happ:\n\n"
        f"<code>{url}</code>"
    )
