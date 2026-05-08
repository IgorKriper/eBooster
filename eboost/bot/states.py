from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AccessFlow(StatesGroup):
    waiting_promo_code = State()
    waiting_receipt_email = State()


class AdminPromoFlow(StatesGroup):
    waiting_code = State()
    waiting_discount = State()
    waiting_valid_days = State()
    waiting_limit = State()
    waiting_disable_code = State()


class AdminBroadcastFlow(StatesGroup):
    waiting_text = State()
    confirming = State()


class AdminUserFlow(StatesGroup):
    waiting_user_id = State()
    waiting_give_user_id = State()
    waiting_give_days = State()
    waiting_disable_user_id = State()
