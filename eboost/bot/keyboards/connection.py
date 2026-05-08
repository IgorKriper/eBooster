from __future__ import annotations

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup


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


def device_connection_menu(*, device: str, open_url: str, back_to: str = "connect") -> InlineKeyboardMarkup:
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
            [InlineKeyboardButton(text="📋 Скопировать", copy_text=CopyTextButton(text=url))],
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
