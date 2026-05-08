from eboost.bot.keyboards.access import (
    active_access_menu,
    after_payment_menu,
    payment_menu,
    plans_menu,
    promo_applied_menu,
    promo_invalid_menu,
    promo_question_menu,
)
from eboost.bot.keyboards.admin import (
    admin_broadcast_segments_menu,
    admin_broadcast_confirm_menu,
    admin_server_toggle_menu,
    admin_servers_menu,
    admin_menu,
    admin_promos_menu,
)
from eboost.bot.keyboards.cabinet import cabinet_menu, cabinet_no_access_menu, payment_history_empty_menu
from eboost.bot.keyboards.common import back_menu
from eboost.bot.keyboards.connection import (
    connect_action_menu,
    device_card_menu,
    device_connection_menu,
    device_instruction_menu,
    device_menu,
    ready_menu,
)
from eboost.bot.keyboards.documents import documents_menu
from eboost.bot.keyboards.info import info_menu, support_menu
from eboost.bot.keyboards.main import main_menu
from eboost.bot.keyboards.referral import referral_menu
from eboost.bot.keyboards.trial import trial_already_used_menu, trial_offer_menu

__all__ = [
    "admin_broadcast_segments_menu",
    "admin_broadcast_confirm_menu",
    "admin_menu",
    "admin_promos_menu",
    "admin_server_toggle_menu",
    "admin_servers_menu",
    "active_access_menu",
    "after_payment_menu",
    "back_menu",
    "cabinet_menu",
    "cabinet_no_access_menu",
    "connect_action_menu",
    "device_card_menu",
    "device_connection_menu",
    "device_instruction_menu",
    "device_menu",
    "documents_menu",
    "info_menu",
    "main_menu",
    "payment_history_empty_menu",
    "payment_menu",
    "plans_menu",
    "promo_applied_menu",
    "promo_invalid_menu",
    "promo_question_menu",
    "referral_menu",
    "ready_menu",
    "support_menu",
    "trial_already_used_menu",
    "trial_offer_menu",
]
