from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class AccessFlow(StatesGroup):
    waiting_promo_code = State()
