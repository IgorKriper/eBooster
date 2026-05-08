"""Central branding constants for eBooster (texts shown to users)."""
from __future__ import annotations

BRAND_NAME = "eBooster"
SUPPORT_USERNAME_DEFAULT = "@eBooster_support"
WELCOME_LOGO_PATH = "eboost/assets/ebooster_logo.png"

BRAND_TAGLINE_SHORT = "Стабильный интернет без сложных настроек"
BRAND_TAGLINE_LONG = (
    "eBooster — простой и быстрый интернет-ускоритель. Подключение за минуту, "
    "поддержка iOS, Android, macOS и Windows, до 4 устройств в одной подписке."
)

# 1024-symbol limit for Telegram photo caption — keep welcome below that.
WELCOME_MESSAGE = (
    "<b>🚀 Добро пожаловать в eBooster</b>\n\n"
    "Стабильный интернет без сложных настроек.\n\n"
    "<b>Что внутри:</b>\n"
    "• Быстрое подключение через приложение Happ\n"
    "• До 4 устройств в одной подписке\n"
    "• iOS, Android, macOS, Windows\n"
    "• Ускоренное и стабильное соединение\n"
    "• Без логов и без рекламы\n\n"
    "<b>3 дня бесплатно</b> — без карты, без обязательств.\n"
    "Нажми кнопку ниже, чтобы начать."
)

WELCOME_MESSAGE_WITH_ACTIVE_SUB = (
    "<b>🚀 eBooster</b>\n\n"
    "Подписка активна — жми «🚀 Открыть и подключить», чтобы добавить eBooster в Happ "
    "или продолжить пользоваться сервисом."
)

WELCOME_MESSAGE_EXPIRED = (
    "<b>🚀 eBooster</b>\n\n"
    "Подписка eBooster закончилась. Продли тариф или активируй реферальную программу, "
    "чтобы вернуться к стабильному интернету."
)

BOT_SHORT_DESCRIPTION = "eBooster — стабильный интернет без сложных настроек."
BOT_LONG_DESCRIPTION = (
    "eBooster — Telegram-сервис для быстрого и стабильного интернета.\n\n"
    "• 3 дня бесплатно\n"
    "• До 4 устройств в одной подписке\n"
    "• iOS, Android, macOS, Windows\n"
    "• Подключение через приложение Happ за минуту\n\n"
    "Нажми /start, чтобы попробовать."
)
