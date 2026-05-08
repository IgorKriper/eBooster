from __future__ import annotations

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

# Telegram CopyTextButton limit is 256 bytes. We use a callback fallback above
# that — see `copy_link_button` and `copy_link_callback` in the bot router.
COPY_TEXT_BUTTON_MAX_LEN = 256


def device_menu(back_to: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📱 iPhone / iPad", callback_data="device:iphone"),
                InlineKeyboardButton(text="🤖 Android", callback_data="device:android"),
            ],
            [
                InlineKeyboardButton(text="💻 Windows", callback_data="device:windows"),
                InlineKeyboardButton(text="🍏 Mac", callback_data="device:mac"),
            ],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)],
        ]
    )


def copy_link_button(url: str, *, device: str) -> InlineKeyboardButton:
    """CopyTextButton when the URL fits the 256-byte limit, callback fallback otherwise."""
    if len(url.encode("utf-8")) <= COPY_TEXT_BUTTON_MAX_LEN:
        return InlineKeyboardButton(text="📋 Скопировать ссылку", copy_text=CopyTextButton(text=url))
    return InlineKeyboardButton(text="📋 Прислать ссылку сообщением", callback_data=f"copy_link:{device}")


def device_card_menu(
    *,
    device: str,
    open_url: str,
    download_url: str,
    subscription_url: str,
    back_to: str = "connect",
) -> InlineKeyboardMarkup:
    """Platform card S11–S14: one screen with 4 buttons (open, download, copy, back)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть и подключить", url=open_url)],
            [InlineKeyboardButton(text="⬇️ Скачать Happ", url=download_url)],
            [copy_link_button(subscription_url, device=device)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)],
        ]
    )


def device_connection_menu(*, device: str, open_url: str, back_to: str = "connect") -> InlineKeyboardMarkup:
    """Legacy 3-button menu kept for backwards compatibility."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть и подключить", url=open_url)],
            [InlineKeyboardButton(text="📖 Инструкция", callback_data=f"instruction:{device}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)],
        ]
    )


def device_instruction_menu(*, device: str, url: str, back_to: str = "connect") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [copy_link_button(url, device=device)],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)],
        ]
    )


def ready_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Продлить доступ", callback_data="access_extend")],
            [InlineKeyboardButton(text="⬅️ В меню", callback_data="main")],
        ]
    )


def connect_action_menu(open_url: str, back_to: str = "main") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚀 Открыть и подключить", url=open_url)],
            [InlineKeyboardButton(text="📖 Инструкции по устройствам", callback_data="connect_devices")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data=back_to)],
        ]
    )
