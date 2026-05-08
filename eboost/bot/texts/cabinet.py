def _referral_block(invited: int, bonus_days: int) -> str:
    if bonus_days > 0:
        return (
            f"Приглашено друзей: <b>{invited}</b>\n\n"
            "Благодаря приглашённым пользователям\n"
            f"вам добавлено <b>+{bonus_days} дней</b> к подписке."
        )
    return (
        f"Приглашено друзей: <b>{invited}</b>\n\n"
        "Приглашай друзей и получай дополнительные дни к подписке."
    )


def active(date: str, invited: int, bonus_days: int) -> str:
    return (
        "<b>👤 Кабинет</b>\n\n"
        "Доступ: <b>активен</b>\n"
        f"До: <b>{date}</b>\n\n"
        f"{_referral_block(invited, bonus_days)}"
    )


def inactive(invited: int, bonus_days: int) -> str:
    return (
        "<b>👤 Кабинет</b>\n\n"
        "Доступ: <b>не активен</b>\n\n"
        f"Приглашено друзей: <b>{invited}</b>\n\n"
        "Ты можешь активировать доступ или пригласить друзей, чтобы получить бонусные дни."
    )


def payment_history(rows: list[str]) -> str:
    if not rows:
        return "<b>💳 История оплат</b>\n\nУ тебя пока нет оплат."
    return "<b>💳 История оплат</b>\n\n" + "\n".join(rows)
