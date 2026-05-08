from __future__ import annotations


def _referral_block(invited: int, bonus_days: int) -> str:
    if bonus_days > 0:
        return (
            f"Приглашено друзей: <b>{invited}</b>\n"
            f"Бонусных дней начислено: <b>+{bonus_days}</b>"
        )
    return (
        f"Приглашено друзей: <b>{invited}</b>\n"
        "Приглашай друзей и получай бонусные дни."
    )


def active(
    *,
    plan_title: str,
    until: str,
    used_slots: int,
    slot_limit: int,
    invited: int,
    bonus_days: int,
) -> str:
    slot_block = (
        f"Устройств: <b>{used_slots} / {slot_limit}</b>\n" if slot_limit else ""
    )
    return (
        "<b>👤 Кабинет</b>\n\n"
        f"Тариф: <b>{plan_title}</b>\n"
        "Доступ: <b>активен</b>\n"
        f"Доступ до: <b>{until}</b>\n"
        f"{slot_block}\n"
        f"{_referral_block(invited, bonus_days)}"
    )


def trial_active(
    *,
    until: str,
    used_slots: int,
    slot_limit: int,
    invited: int,
    bonus_days: int,
) -> str:
    slot_block = (
        f"Устройств: <b>{used_slots} / {slot_limit}</b>\n" if slot_limit else ""
    )
    return (
        "<b>👤 Кабинет</b>\n\n"
        "Тариф: <b>пробный период</b>\n"
        "Доступ: <b>активен</b>\n"
        f"Доступ до: <b>{until}</b>\n"
        f"{slot_block}\n"
        f"{_referral_block(invited, bonus_days)}"
    )


def inactive(invited: int, bonus_days: int) -> str:
    return (
        "<b>👤 Кабинет</b>\n\n"
        "Доступ: <b>не активен</b>\n\n"
        f"{_referral_block(invited, bonus_days)}\n\n"
        "Можно активировать пробный период или выбрать тариф."
    )


def payment_history(rows: list[str]) -> str:
    if not rows:
        return "<b>🧾 История оплат</b>\n\nУ тебя пока нет оплат."
    return "<b>🧾 История оплат</b>\n\n" + "\n".join(rows)
