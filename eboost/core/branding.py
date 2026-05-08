"""Central branding constants for eBooster (texts shown to users)."""
from __future__ import annotations

BRAND_NAME = "eBooster"
SUPPORT_USERNAME_DEFAULT = "@eBooster_support"
WELCOME_LOGO_PATH = "eboost/assets/ebooster_logo.png"

BRAND_TAGLINE_SHORT = "Стабильный интернет за 1 минуту"
BRAND_TAGLINE_LONG = (
    "eBooster — простой и быстрый ускоритель интернета. "
    "Подключение через приложение Happ, поддержка iOS, Android, macOS, Windows."
)

# Welcome (S01) — короткое и привлекательное приветствие.
# Лимит подписи Telegram (1024) не нужен: фото и текст шлём раздельно.
WELCOME_MESSAGE = (
    "<b>🚀 eBooster</b>\n"
    "Стабильный интернет за 1 минуту.\n\n"
    "• Без рекламы и логов\n"
    "• До 10 устройств в одной подписке\n"
    "• iOS · Android · macOS · Windows\n\n"
    "<b>3 дня бесплатно</b> — без карты."
)

WELCOME_MESSAGE_WITH_ACTIVE_SUB = (
    "<b>🚀 eBooster</b>\n"
    "Подписка активна.\n\n"
    "Жми «🚀 Открыть и подключить», чтобы добавить eBooster в Happ."
)

WELCOME_MESSAGE_EXPIRED = (
    "<b>🚀 eBooster</b>\n"
    "Подписка закончилась.\n\n"
    "Продли тариф — и вернёмся к стабильному интернету."
)

BOT_SHORT_DESCRIPTION = "eBooster — стабильный интернет за 1 минуту."
BOT_LONG_DESCRIPTION = (
    "eBooster — Telegram-сервис для быстрого и стабильного интернета.\n\n"
    "• 3 дня бесплатно\n"
    "• До 10 устройств в одной подписке\n"
    "• iOS, Android, macOS, Windows\n"
    "• Подключение через приложение Happ за минуту\n\n"
    "Нажми /start, чтобы попробовать."
)
