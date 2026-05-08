from __future__ import annotations

from eboost.core.branding import (
    WELCOME_MESSAGE,
    WELCOME_MESSAGE_EXPIRED,
    WELCOME_MESSAGE_WITH_ACTIVE_SUB,
)
from eboost.models import User
from eboost.services.subscriptions import is_subscription_active


def welcome_for(user: User | None, panel: str = "") -> str:
    if user and is_subscription_active(user):
        body = WELCOME_MESSAGE_WITH_ACTIVE_SUB
    elif user and user.subscription_until is not None:
        body = WELCOME_MESSAGE_EXPIRED
    else:
        body = WELCOME_MESSAGE
    if panel:
        return f"{panel}\n\n{body}"
    return body


def main(active_until: str | None = None) -> str:  # noqa: ARG001 — kept for compat
    return WELCOME_MESSAGE


MAIN = WELCOME_MESSAGE
