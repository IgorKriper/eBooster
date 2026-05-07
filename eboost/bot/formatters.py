from __future__ import annotations

from eboost.core.time import as_utc
from eboost.core.time import utcnow
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
