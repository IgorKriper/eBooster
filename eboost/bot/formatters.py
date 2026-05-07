from __future__ import annotations

from eboost.core.branding import BRAND_NAME
from eboost.core.time import as_utc, utcnow
from eboost.models import User
from eboost.services.subscriptions import is_subscription_active


def format_date(user: User) -> str:
    if not user.subscription_until:
        return "нет активного доступа"
    value = as_utc(user.subscription_until)
    return value.strftime("%d.%m.%Y") if value else "нет активного доступа"


def user_status(user: User) -> str:
    if user.is_disabled:
        return "отключен"
    if is_subscription_active(user):
        return "активен"
    if user.subscription_until and user.subscription_until <= utcnow():
        return "закончился"
    return "не активирован"


def _format_remaining(user: User) -> str:
    until = as_utc(user.subscription_until)
    if not until:
        return "—"
    remaining = until - utcnow()
    if remaining.total_seconds() <= 0:
        return "истёк"
    days = remaining.days
    hours = remaining.seconds // 3600
    if days >= 2:
        return f"{days} дн."
    if days == 1:
        return f"1 дн. {hours} ч."
    if hours >= 1:
        return f"{hours} ч."
    minutes = max(remaining.seconds // 60, 1)
    return f"{minutes} мин."


def format_subscription_panel(user: User) -> str:
    if not is_subscription_active(user):
        return f"⏳ Подписка {BRAND_NAME} закончилась. Чтобы снова подключиться к ускорению, продли подписку."
    return (
        f"✅ Подписка {BRAND_NAME} активна\n"
        f"⏳ Доступ до: {format_date(user)} ({_format_remaining(user)})\n"
        f"📱 Устройства: до {user.device_limit}"
    )
