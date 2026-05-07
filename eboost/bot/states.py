from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AccessFlow(StatesGroup):
    waiting_promo_code = State()


class AdminFlow(StatesGroup):
    waiting_user_id = State()
    waiting_give_id = State()
    waiting_give_days = State()
    waiting_disable_id = State()
    waiting_broadcast_text = State()
