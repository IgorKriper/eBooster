from __future__ import annotations

import html
import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.bot import keyboards
from eboost.bot.formatters import format_date, format_subscription_panel
from eboost.bot.states import AccessFlow
from eboost.bot.texts import access as access_texts
from eboost.bot.texts import cabinet as cabinet_texts
from eboost.bot.texts import connection as connection_texts
from eboost.bot.texts import documents as document_texts
from eboost.bot.texts import info as info_texts
from eboost.bot.texts import referral as referral_texts
from eboost.bot.texts import start as start_texts
from eboost.bot.texts import trial as trial_texts
from eboost.core.config import get_settings
from eboost.core.time import utcnow
from eboost.models import Plan
from eboost.models.payment import PaymentStatus
from eboost.models.plan import PLAN_KIND_DEVICE_PACK
from eboost.services import (
    connect_tokens,
    documents,
    happ,
    payments,
    plans,
    promo_codes,
    referrals,
    trials,
    users,
)
from eboost.services.payment.factory import get_payment_provider
from eboost.services.subscriptions import is_subscription_active
from eboost.services.vpn.factory import get_vpn_provider

logger = logging.getLogger(__name__)

router = Router()


async def ensure_user(message_or_callback: Message | CallbackQuery, session: AsyncSession):
    tg_user = message_or_callback.from_user
    return await users.get_or_create_user(
        session,
        telegram_id=tg_user.id,
        username=tg_user.username,
        first_name=tg_user.first_name,
    )


async def _send_welcome(message: Message, user) -> None:
    settings = get_settings()
    panel = format_subscription_panel(user)
    text = start_texts.welcome_for(user, panel=panel)
    markup = keyboards.main_menu(user)
    logo_path = Path(settings.welcome_logo_path) if settings.welcome_logo_path else None
    if logo_path and logo_path.is_file():
        try:
            await message.answer_photo(
                FSInputFile(str(logo_path)),
                caption=text,
                reply_markup=markup,
            )
            return
        except Exception:
            logger.exception("welcome_photo_failed path=%s", logo_path)
    await message.answer(text, reply_markup=markup)


async def render_main(target: Message | CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(target, session)
    panel = format_subscription_panel(user)
    text = start_texts.welcome_for(user, panel=panel)
    markup = keyboards.main_menu(user)
    if isinstance(target, Message):
        await _send_welcome(target, user)
    else:
        try:
            await target.message.edit_text(text, reply_markup=markup)
        except Exception:
            await target.message.answer(text, reply_markup=markup)
        await target.answer()


@router.message(CommandStart())
async def start(message: Message, command: CommandObject, session: AsyncSession) -> None:
    user = await users.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        start_payload=command.args,
    )
    await _send_welcome(message, user)


@router.message(Command("id"))
async def my_id(message: Message) -> None:
    await message.answer(f"Твой Telegram ID: <code>{message.from_user.id}</code>")


@router.callback_query(F.data == "main")
async def main_callback(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    await state.clear()
    await render_main(callback, session)


@router.callback_query(F.data == "trial")
async def trial_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await ensure_user(callback, session)
    if user.trial_started_at:
        await callback.message.edit_text(trial_texts.ALREADY_USED, reply_markup=keyboards.trial_already_used_menu())
    else:
        await callback.message.edit_text(trial_texts.OFFER, reply_markup=keyboards.trial_offer_menu())
    await callback.answer()


@router.callback_query(F.data == "trial_activate")
async def trial_activate_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await ensure_user(callback, session)
    activated, _ = await trials.activate_trial(
        session,
        user=user,
        settings=settings,
        vpn_provider=get_vpn_provider(settings),
    )
    if activated:
        await callback.message.edit_text(trial_texts.ACTIVATED, reply_markup=keyboards.device_menu("access"))
    else:
        await callback.message.edit_text(trial_texts.ALREADY_USED, reply_markup=keyboards.trial_already_used_menu())
    await callback.answer()


@router.callback_query(F.data == "access")
async def access_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await ensure_user(callback, session)
    if is_subscription_active(user):
        await callback.message.edit_text(
            access_texts.active_until(format_date(user)),
            reply_markup=keyboards.active_access_menu(),
        )
    else:
        await show_plan_list(callback, session, back_to="main")
    await callback.answer()


@router.callback_query(F.data == "access_extend")
async def access_extend_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    await show_plan_list(callback, session, back_to="access")
    await callback.answer()


async def show_plan_list(callback: CallbackQuery, session: AsyncSession, *, back_to: str) -> None:
    active_plans = await plans.list_active_plans(session)
    await callback.message.edit_text(
        access_texts.plans(),
        reply_markup=keyboards.plans_menu(active_plans, back_to=back_to),
    )


@router.callback_query(F.data.startswith("plan:"))
async def plan_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    plan_id = int(callback.data.split(":", 1)[1])
    plan = await plans.get_plan(session, plan_id)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    await state.update_data(plan_id=plan.id, promo_code=None)
    await callback.message.edit_text(
        access_texts.selected_plan(plan.title, plan.price_rub, plan.duration_days),
        reply_markup=keyboards.promo_question_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "promo_enter")
async def promo_enter_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AccessFlow.waiting_promo_code)
    await callback.message.edit_text(access_texts.PROMO_ENTER, reply_markup=keyboards.back_menu("access"))
    await callback.answer()


@router.message(AccessFlow.waiting_promo_code)
async def promo_code_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    plan = await _plan_from_state(session, state)
    user = await ensure_user(message, session)
    if not plan:
        await state.clear()
        await message.answer(access_texts.plans(), reply_markup=keyboards.main_menu(user))
        return

    validation = await promo_codes.validate_promo_code(session, user=user, code=message.text or "")
    if not validation.is_valid or validation.promo_code is None:
        await message.answer(access_texts.PROMO_INVALID, reply_markup=keyboards.promo_invalid_menu())
        return

    final_amount = promo_codes.apply_discount(plan.price_rub, validation.promo_code.discount_percent)
    await state.update_data(promo_code=validation.promo_code.code)
    await state.set_state(None)
    await message.answer(
        access_texts.promo_applied(plan.title, validation.promo_code.discount_percent, final_amount),
        reply_markup=keyboards.promo_applied_menu(),
    )


async def create_payment_from_state(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    *,
    use_promo: bool,
) -> None:
    selected_plan = await _plan_from_state(session, state)
    if not selected_plan:
        await callback.answer("Выбери тариф заново", show_alert=True)
        return

    settings = get_settings()
    provider = get_payment_provider(settings)
    user = await ensure_user(callback, session)
    data = await state.get_data()

    try:
        if provider.name == "yookassa":
            payment = await payments.create_deferred_payment(
                session,
                user=user,
                plan=selected_plan,
                payment_provider=provider,
                settings=settings,
                promo_code=data.get("promo_code") if use_promo else None,
            )
        else:
            payment = await payments.create_payment(
                session,
                user=user,
                plan=selected_plan,
                payment_provider=provider,
                promo_code=data.get("promo_code") if use_promo else None,
            )
    except ValueError:
        await callback.message.edit_text(access_texts.PROMO_INVALID, reply_markup=keyboards.promo_invalid_menu())
        await callback.answer()
        return
    except RuntimeError:
        await callback.message.edit_text(access_texts.PAYMENT_UNAVAILABLE, reply_markup=keyboards.back_menu("access"))
        await callback.answer()
        return

    await callback.message.edit_text(
        access_texts.payment_created(selected_plan.title, payment.final_amount),
        reply_markup=keyboards.payment_menu(payment),
    )
    await callback.answer()


@router.message(AccessFlow.waiting_receipt_email)
async def receipt_email_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    email = (message.text or "").strip()
    if not _looks_like_receipt_email(email):
        await message.answer(access_texts.RECEIPT_EMAIL_INVALID, reply_markup=keyboards.back_menu("access"))
        return

    await state.update_data(receipt_email=email)
    await state.set_state(None)
    selected_plan = await _plan_from_state(session, state)
    user = await ensure_user(message, session)
    if not selected_plan:
        await state.clear()
        await message.answer(access_texts.plans(), reply_markup=keyboards.main_menu(user))
        return

    settings = get_settings()
    provider = get_payment_provider(settings)
    data = await state.get_data()
    use_promo = bool(data.get("pending_use_promo"))
    try:
        payment = await _create_payment_from_state_data(
            session,
            user=user,
            plan=selected_plan,
            provider=provider,
            data=data,
            use_promo=use_promo,
        )
    except ValueError:
        await message.answer(access_texts.PROMO_INVALID, reply_markup=keyboards.promo_invalid_menu())
        return
    except RuntimeError:
        await message.answer(access_texts.PAYMENT_UNAVAILABLE, reply_markup=keyboards.back_menu("access"))
        return

    await message.answer(
        access_texts.payment_created(selected_plan.title, payment.final_amount),
        reply_markup=keyboards.payment_menu(payment),
    )


async def _create_payment_from_state_data(
    session: AsyncSession,
    *,
    user,
    plan: Plan,
    provider,
    data: dict,
    use_promo: bool,
):
    return await payments.create_payment(
        session,
        user=user,
        plan=plan,
        payment_provider=provider,
        promo_code=data.get("promo_code") if use_promo else None,
        customer_email=data.get("receipt_email"),
    )


def _has_receipt_contact(settings, data: dict) -> bool:
    return bool(
        data.get("receipt_email")
        or settings.yookassa_receipt_email.strip()
        or settings.yookassa_receipt_phone.strip()
    )


def _looks_like_receipt_email(value: str) -> bool:
    if not value or len(value) > 254 or " " in value:
        return False
    local, sep, domain = value.partition("@")
    return bool(local and sep and "." in domain and not domain.startswith(".") and not domain.endswith("."))


async def _plan_from_state(session: AsyncSession, state: FSMContext) -> Plan | None:
    data = await state.get_data()
    plan_id = data.get("plan_id")
    return await plans.get_plan(session, int(plan_id)) if plan_id else None


@router.callback_query(F.data == "pay_without_promo")
async def pay_without_promo(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await create_payment_from_state(callback, session, state, use_promo=False)


@router.callback_query(F.data == "pay_with_promo")
async def pay_with_promo(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await create_payment_from_state(callback, session, state, use_promo=True)


@router.callback_query(F.data.startswith("mock_pay:"))
async def mock_pay_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    payment_id = int(callback.data.split(":", 1)[1])
    settings = get_settings()
    try:
        await payments.complete_payment(
            session,
            payment_id=payment_id,
            status=PaymentStatus.SUCCEEDED,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError:
        await callback.answer("Платёж не найден", show_alert=True)
        return

    await callback.message.edit_text(access_texts.PAYMENT_SUCCESS, reply_markup=keyboards.after_payment_menu())
    await callback.answer("Оплата прошла")


@router.callback_query(F.data.startswith("payment_check:"))
async def payment_check(callback: CallbackQuery, session: AsyncSession) -> None:
    payment_id = int(callback.data.split(":", 1)[1])
    user = await ensure_user(callback, session)
    payment = await payments.get_payment_for_user(session, payment_id=payment_id, user_id=user.id)
    if not payment:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    if payment.status != PaymentStatus.SUCCEEDED and payment.provider == "mock":
        settings = get_settings()
        payment = await payments.complete_payment(
            session,
            payment_id=payment.id,
            status=PaymentStatus.SUCCEEDED,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    elif payment.status != PaymentStatus.SUCCEEDED and payment.external_id:
        settings = get_settings()
        provider = get_payment_provider(settings)
        if provider.name == payment.provider:
            try:
                webhook = await provider.get_payment_status(external_id=payment.external_id, payment_id=payment.id)
                if webhook:
                    payment = await payments.handle_provider_webhook(
                        session,
                        webhook=webhook,
                        settings=settings,
                        vpn_provider=get_vpn_provider(settings),
                    )
            except (RuntimeError, ValueError):
                pass
    if payment.status != PaymentStatus.SUCCEEDED:
        await callback.answer("Оплата пока не прошла", show_alert=True)
        return
    await callback.message.edit_text(access_texts.PAYMENT_SUCCESS, reply_markup=keyboards.after_payment_menu())
    await callback.answer()


@router.callback_query(F.data == "connect")
async def connect_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    if not is_subscription_active(user) or not user.vpn_subscription_url:
        await callback.message.edit_text(connection_texts.NO_ACCESS, reply_markup=keyboards.trial_already_used_menu())
        await callback.answer()
        return

    settings = get_settings()
    token = await connect_tokens.issue_connect_token(session, user=user, settings=settings)
    public_url = happ.public_connect_url(settings, token.token)
    await callback.message.edit_text(
        access_texts.connect_panel(public_url),
        reply_markup=keyboards.connect_action_menu(public_url),
    )
    await callback.answer()


@router.callback_query(F.data == "connect_devices")
async def connect_devices_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    if not is_subscription_active(user) or not user.vpn_subscription_url:
        await callback.message.edit_text(connection_texts.NO_ACCESS, reply_markup=keyboards.trial_already_used_menu())
    else:
        await callback.message.edit_text(connection_texts.DEVICE_SELECT, reply_markup=keyboards.device_menu("access"))
    await callback.answer()


@router.callback_query(F.data == "device_pack")
async def device_pack_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await ensure_user(callback, session)
    if not is_subscription_active(user):
        await callback.message.edit_text(connection_texts.NO_ACCESS, reply_markup=keyboards.trial_already_used_menu())
        await callback.answer()
        return
    packs = await plans.list_device_packs(session)
    await callback.message.edit_text(
        access_texts.device_packs(user.device_limit),
        reply_markup=keyboards.plans_menu(packs, back_to="main"),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("device:"))
async def device_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    device = callback.data.split(":", 1)[1]
    user = await ensure_user(callback, session)
    if not is_subscription_active(user) or not user.vpn_subscription_url:
        await callback.message.edit_text(connection_texts.NO_ACCESS, reply_markup=keyboards.trial_already_used_menu())
        await callback.answer()
        return
    if user.connected_at is None:
        user.connected_at = utcnow()
    settings = get_settings()
    await callback.message.edit_text(
        connection_texts.CONNECT,
        reply_markup=keyboards.device_connection_menu(
            device=device,
            open_url=happ.connect_url(settings, user.telegram_id),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("copy_link:"))
async def copy_link_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    device = callback.data.split(":", 1)[1]
    user = await ensure_user(callback, session)
    if not user.vpn_subscription_url:
        await callback.answer("Ссылка пока недоступна", show_alert=True)
        return
    await callback.message.edit_text(
        connection_texts.copy_link(user.vpn_subscription_url),
        reply_markup=keyboards.device_instruction_menu(
            device=device,
            url=user.vpn_subscription_url,
            back_to=f"device:{device}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("instruction:"))
async def instruction_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    device = callback.data.split(":", 1)[1]
    user = await ensure_user(callback, session)
    if not is_subscription_active(user) or not user.vpn_subscription_url:
        await callback.message.edit_text(connection_texts.NO_ACCESS, reply_markup=keyboards.trial_already_used_menu())
        await callback.answer()
        return
    await callback.message.edit_text(
        connection_texts.INSTRUCTIONS.get(device, connection_texts.CONNECT),
        reply_markup=keyboards.device_instruction_menu(
            device=device,
            url=user.vpn_subscription_url,
            back_to=f"device:{device}",
        ),
    )
    await callback.answer()


@router.callback_query(F.data == "cabinet")
async def cabinet_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    stats = await referrals.referral_stats(session, referrer_id=user.id, settings=get_settings())
    if is_subscription_active(user):
        text = cabinet_texts.active(format_date(user), stats.invited_count, stats.bonus_days)
        markup = keyboards.cabinet_menu()
    else:
        text = cabinet_texts.inactive(stats.invited_count, stats.bonus_days)
        markup = keyboards.cabinet_no_access_menu()
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "invite")
async def invite_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    bot_username = (await callback.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user.referral_code}"
    stats = await referrals.referral_stats(session, referrer_id=user.id, settings=get_settings())
    await callback.message.edit_text(
        referral_texts.referral(link, stats.invited_count, stats.bonus_days, stats.friends_until_bonus),
        reply_markup=keyboards.referral_menu(link),
    )
    await callback.answer()


@router.callback_query(F.data == "payments_history")
async def payments_history_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    items = await payments.list_user_payments(session, user.id)
    rows = [
        f"{payment.created_at.strftime('%d.%m.%Y')} - <b>{payment.final_amount}₽</b> - {html.escape(payment.plan.title)} - оплачено"
        for payment in items
        if payment.status == PaymentStatus.SUCCEEDED
    ]
    markup = keyboards.back_menu("cabinet") if rows else keyboards.payment_history_empty_menu()
    await callback.message.edit_text(cabinet_texts.payment_history(rows), reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data == "info")
async def info_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(info_texts.INFO, reply_markup=keyboards.info_menu())
    await callback.answer()


@router.callback_query(F.data == "info_instruction")
async def info_instruction_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        connection_texts.INSTRUCTION_SELECT,
        reply_markup=keyboards.device_menu("info"),
    )
    await callback.answer()


@router.callback_query(F.data == "documents")
async def documents_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    docs = await documents.list_documents(session)
    await callback.message.edit_text(
        document_texts.LIST,
        reply_markup=keyboards.documents_menu([(doc.slug, doc.title) for doc in docs]),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("doc:"))
async def document_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    slug = callback.data.split(":", 1)[1]
    document = await documents.get_document(session, slug)
    if not document:
        await callback.answer("Документ не найден", show_alert=True)
        return
    await callback.message.edit_text(document.body, reply_markup=keyboards.back_menu("documents", "⬅️ Назад к документам"))
    await callback.answer()


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery) -> None:
    settings = get_settings()
    await callback.message.edit_text(info_texts.SUPPORT, reply_markup=keyboards.support_menu(settings.support_username))
    await callback.answer()
