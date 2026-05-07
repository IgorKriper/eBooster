"""Centralised brand-facing constants for eBooster.

Internal package/table/env names intentionally keep historical ``eboost``
spelling to avoid breaking migrations and external integrations.  Anything
the user can read in the bot or on the connect page must come from here.
"""
from __future__ import annotations

from pathlib import Path

BRAND_NAME: str = "eBooster"
BRAND_NAME_LOWER: str = "ebooster"
SUPPORT_USERNAME_DEFAULT: str = "@eBooster_support"

ASSETS_DIR: Path = Path(__file__).resolve().parent.parent / "assets"
WELCOME_LOGO_FILENAME: str = "ebooster_logo.png"
WELCOME_LOGO_PATH: Path = ASSETS_DIR / WELCOME_LOGO_FILENAME

BRAND_TAGLINE_SHORT: str = (
    "eBooster — быстрый и безопасный VPN-ускоритель. Подключение за пару минут, "
    "пробный период, до 4 устройств в подписке."
)

BRAND_TAGLINE_LONG: str = (
    "eBooster помогает быстро и удобно подключиться к защищённому VPN-доступу для "
    "повседневного использования: сайты, приложения, работа, общение и видео.\n\n"
    "Преимущества:\n"
    "• 🚀 быстрое подключение без сложных настроек;\n"
    "• 🔐 приватный доступ и защита соединения;\n"
    "• 📱 до 4 устройств в одной подписке;\n"
    "• 🧩 поддержка iOS, Android, macOS и Windows;\n"
    "• ⚡ простая активация через приложение Happ;\n"
    "• 💬 понятная инструкция без ручного копирования ссылок.\n\n"
    "После активации достаточно нажать кнопку — откроется инструкция, и подписка "
    "автоматически добавится в Happ."
)

WELCOME_MESSAGE: str = (
    "👋 <b>Добро пожаловать в eBooster!</b>\n\n"
    "<b>eBooster</b> помогает быстро и удобно подключиться к защищённому VPN-"
    "доступу для повседневного использования: сайты, приложения, работа, общение, "
    "видео и другие сервисы.\n\n"
    "<b>Что внутри:</b>\n"
    "• 🚀 быстрое подключение без сложных настроек;\n"
    "• 🔐 приватный доступ и защита подключения;\n"
    "• 📱 до 4 устройств в одной подписке;\n"
    "• 🧩 поддержка iOS, Android, macOS и Windows;\n"
    "• ⚡ простая активация через приложение Happ;\n"
    "• 💬 понятная инструкция без ручного копирования ссылок.\n\n"
    "Мы сделали подключение максимально простым: после активации ты нажимаешь "
    "кнопку, открывается инструкция eBooster, и подписка автоматически добавляется "
    "в Happ.\n\n"
    "<b>Начни с пробного периода и проверь скорость сам.</b>"
)

WELCOME_MESSAGE_WITH_ACTIVE_SUB: str = (
    "👋 <b>С возвращением в eBooster!</b>\n\n"
    "Подписка активна. Нажми «🚀 Открыть и подключить», чтобы добавить eBooster "
    "в Happ или настроить новое устройство."
)

WELCOME_MESSAGE_EXPIRED: str = (
    "⏳ <b>Подписка eBooster закончилась</b>\n\n"
    "Чтобы снова подключиться к ускорению, продли подписку. Можно использовать "
    "пробный период повторно нельзя — выбери подходящий тариф ниже."
)

BOT_SHORT_DESCRIPTION: str = (
    "eBooster — быстрый и безопасный VPN-ускоритель. Пробный период, до 4 устройств "
    "и подключение за пару минут."
)

BOT_LONG_DESCRIPTION: str = (
    "eBooster — быстрый и безопасный VPN-ускоритель для доступа к любимым "
    "сервисам, приложениям и сайтам.\n\n"
    "• Пробный период — попробуй бесплатно.\n"
    "• До 4 устройств в одной подписке.\n"
    "• Поддержка iOS, Android, macOS и Windows.\n"
    "• Простая активация через приложение Happ — без ручного копирования ссылок.\n\n"
    "Нажми «Запустить», чтобы начать."
)
