from __future__ import annotations

import logging
from pathlib import Path

from aiogram import F, Router
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, FSInputFile, Message
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.bot import keyboards
from eboost.bot.formatters import (
    format_date,
    format_subscription_panel,
    user_status,
)
from eboost.bot.states import AccessFlow
from eboost.core.branding import (
    BRAND_NAME,
    WELCOME_MESSAGE,
    WELCOME_MESSAGE_EXPIRED,
)
from eboost.core.config import Settings, get_settings
from eboost.models.payment import PaymentStatus
from eboost.models.plan import PLAN_KIND_DEVICE_PACK, PLAN_KIND_SUBSCRIPTION
from eboost.services import (
    connect_tokens,
    documents,
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


def _build_connect_url(token: str, settings: Settings) -> str:
    base = (settings.effective_connect_public_url or "").rstrip("/")
    if not base:
        return f"/connect?token={token}"
    return f"{base}/connect?token={token}"


async def _connect_url_for(
    session: AsyncSession,
    *,
    user,
    settings: Settings,
) -> str | None:
    if not user.vpn_subscription_url:
        return None
    token = await connect_tokens.issue_connect_token(session, user=user, settings=settings)
    return _build_connect_url(token.token, settings)


def _welcome_text_for(user) -> str:
    if is_subscription_active(user):
        return WELCOME_MESSAGE
    if user.subscription_until is not None:
        return WELCOME_MESSAGE_EXPIRED
    return WELCOME_MESSAGE


async def _send_welcome(message: Message, user) -> None:
    settings = get_settings()
    text = _welcome_text_for(user)
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


async def render_main(
    target: Message | CallbackQuery,
    *,
    user,
    text: str | None = None,
) -> None:
    body = text or _welcome_text_for(user)
    markup = keyboards.main_menu(user)
    if isinstance(target, Message):
        await target.answer(body, reply_markup=markup)
        return
    try:
        await target.message.edit_text(body, reply_markup=markup)
    except Exception:
        await target.message.answer(body, reply_markup=markup)
    await target.answer()


@router.message(CommandStart())
async def start(
    message: Message,
    command: CommandObject,
    session: AsyncSession,
    state: FSMContext,
) -> None:
    await state.clear()
    user = await users.get_or_create_user(
        session,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        start_payload=command.args,
    )
    await _send_welcome(message, user)


@router.callback_query(F.data == "main")
async def main_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await ensure_user(callback, session)
    await render_main(callback, user=user)


@router.callback_query(F.data == "trial")
async def trial_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    vpn_provider = get_vpn_provider(settings)
    user = await ensure_user(callback, session)
    activated, message = await trials.activate_trial(
        session, user=user, settings=settings, vpn_provider=vpn_provider
    )
    if activated:
        connect_url = await _connect_url_for(session, user=user, settings=settings)
        text = (
            f"✅ {message}\n\n"
            f"{format_subscription_panel(user)}\n\n"
            f"Жми «🚀 Открыть и подключить» — откроется бренд-страница {BRAND_NAME} "
            "с инструкцией и кнопкой добавления подписки в Happ."
        )
        markup = (
            keyboards.connect_open_menu(connect_url)
            if connect_url
            else keyboards.connect_unavailable_menu()
        )
        await callback.message.edit_text(text, reply_markup=markup)
    else:
        await callback.message.edit_text(
            f"{message}\n\nДоступ до: {format_date(user)}",
            reply_markup=keyboards.main_menu(user),
        )
    await callback.answer()


@router.callback_query(F.data == "access")
async def access_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    active_plans = await plans.list_active_plans(session)
    await callback.message.edit_text(
        f"Выбери срок доступа в {BRAND_NAME}:",
        reply_markup=keyboards.plans_menu(active_plans),
    )
    await callback.answer()


@router.callback_query(F.data == "add_device")
async def add_device_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await state.clear()
    user = await ensure_user(callback, session)
    if not is_subscription_active(user):
        await callback.answer(
            "Сначала активируй подписку, потом сможешь добавить устройства.",
            show_alert=True,
        )
        await callback.message.edit_text(
            "Сначала активируй подписку — после этого появится возможность добавить устройства.",
            reply_markup=keyboards.main_menu(user),
        )
        return
    packs = await plans.list_active_device_packs(session)
    if not packs:
        await callback.answer("Доп. устройства временно недоступны", show_alert=True)
        return
    await callback.message.edit_text(
        (
            "➕ Добавить устройство\n\n"
            f"Сейчас доступно {user.device_limit} устройств. Выбери пакет, чтобы расширить лимит:"
        ),
        reply_markup=keyboards.device_packs_menu(packs),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("plan:"))
async def plan_callback(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    plan_id = int(callback.data.split(":", 1)[1])
    plan = await plans.get_plan(session, plan_id)
    if not plan:
        await callback.answer("Тариф не найден", show_alert=True)
        return
    await state.update_data(plan_id=plan.id, promo_code=None)
    if plan.kind == PLAN_KIND_DEVICE_PACK:
        await callback.message.edit_text(
            (
                f"Пакет: {plan.title} — {plan.price_rub}₽\n"
                f"Лимит увеличится на +{plan.bonus_devices} устройств.\n\n"
                "У тебя есть промокод?"
            ),
            reply_markup=keyboards.promo_question_menu(),
        )
    else:
        await callback.message.edit_text(
            f"Ты выбрал тариф:\n\n{plan.title} — {plan.price_rub}₽\n\nУ тебя есть промокод?",
            reply_markup=keyboards.promo_question_menu(),
        )
    await callback.answer()


@router.callback_query(F.data == "promo_enter")
async def promo_enter_callback(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(AccessFlow.waiting_promo_code)
    await callback.message.edit_text("Введи промокод одним сообщением:", reply_markup=keyboards.back_menu("access"))
    await callback.answer()


@router.message(AccessFlow.waiting_promo_code)
async def promo_code_message(message: Message, session: AsyncSession, state: FSMContext) -> None:
    data = await state.get_data()
    plan_id = data.get("plan_id")
    plan = await plans.get_plan(session, int(plan_id)) if plan_id else None
    user = await ensure_user(message, session)
    if not plan:
        await state.clear()
        await message.answer("Выбери тариф заново.", reply_markup=keyboards.main_menu(user))
        return

    validation = await promo_codes.validate_promo_code(session, user=user, code=message.text or "")
    if not validation.is_valid or validation.promo_code is None:
        await message.answer(validation.reason or "Промокод не найден или недоступен", reply_markup=keyboards.promo_invalid_menu())
        return

    final_amount = promo_codes.apply_discount(plan.price_rub, validation.promo_code.discount_percent)
    await state.update_data(promo_code=validation.promo_code.code)
    await state.set_state(None)
    await message.answer(
        "Промокод применён ✅\n\n"
        f"Тариф: {plan.title}\n"
        f"Скидка: {validation.promo_code.discount_percent}%\n"
        f"Итого: {final_amount}₽",
        reply_markup=keyboards.promo_applied_menu(),
    )


async def create_payment_from_state(
    callback: CallbackQuery,
    session: AsyncSession,
    state: FSMContext,
    *,
    use_promo: bool,
) -> None:
    data = await state.get_data()
    plan_id = data.get("plan_id")
    selected_plan = await plans.get_plan(session, int(plan_id)) if plan_id else None
    if not selected_plan:
        await callback.answer("Выбери тариф заново", show_alert=True)
        return

    settings = get_settings()
    provider = get_payment_provider(settings)
    user = await ensure_user(callback, session)
    try:
        payment = await payments.create_payment(
            session,
            user=user,
            plan=selected_plan,
            payment_provider=provider,
            promo_code=data.get("promo_code") if use_promo else None,
        )
    except ValueError as exc:
        await callback.message.edit_text(str(exc), reply_markup=keyboards.promo_invalid_menu())
        await callback.answer()
        return

    await callback.message.edit_text(
        f"Почти готово.\n\nТариф: {selected_plan.title}\nК оплате: {payment.final_amount}₽",
        reply_markup=keyboards.payment_menu(payment),
    )
    await callback.answer()


@router.callback_query(F.data == "pay_without_promo")
async def pay_without_promo(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await create_payment_from_state(callback, session, state, use_promo=False)


@router.callback_query(F.data == "pay_with_promo")
async def pay_with_promo(callback: CallbackQuery, session: AsyncSession, state: FSMContext) -> None:
    await create_payment_from_state(callback, session, state, use_promo=True)


async def _render_payment_success(
    callback: CallbackQuery,
    session: AsyncSession,
    payment,
) -> None:
    settings = get_settings()
    user = payment.user
    connect_url = await _connect_url_for(session, user=user, settings=settings)
    is_device_pack = payment.plan.kind == PLAN_KIND_DEVICE_PACK
    if is_device_pack:
        text = (
            "✅ Дополнительные устройства добавлены\n\n"
            f"📱 Устройства: 0 из {user.device_limit}\n"
            f"⏳ Доступ до: {format_date(user)}"
        )
    else:
        text = (
            "✅ Оплата прошла успешно!\n\n"
            f"Подписка {BRAND_NAME} активирована.\n\n"
            f"{format_subscription_panel(user)}\n\n"
            f"Жми «🚀 Открыть и подключить» — откроется бренд-страница {BRAND_NAME} "
            "и подписка автоматически добавится в Happ."
        )
    markup = (
        keyboards.connect_open_menu(connect_url)
        if connect_url
        else keyboards.connect_unavailable_menu()
    )
    await callback.message.edit_text(text, reply_markup=markup)


@router.callback_query(F.data.startswith("mock_pay:"))
async def mock_pay_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    payment_id = int(callback.data.split(":", 1)[1])
    settings = get_settings()
    vpn_provider = get_vpn_provider(settings)
    try:
        payment = await payments.complete_payment(
            session,
            payment_id=payment_id,
            status=PaymentStatus.SUCCEEDED,
            settings=settings,
            vpn_provider=vpn_provider,
        )
    except ValueError:
        await callback.answer("Платёж не найден", show_alert=True)
        return
    await _render_payment_success(callback, session, payment)
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
        user = payment.user
    if payment.status != PaymentStatus.SUCCEEDED:
        await callback.answer("Оплата пока не прошла", show_alert=True)
        return
    await _render_payment_success(callback, session, payment)
    await callback.answer()


@router.callback_query(F.data == "connect")
async def connect_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    settings = get_settings()
    user = await ensure_user(callback, session)
    if not is_subscription_active(user) or not user.vpn_subscription_url:
        await callback.message.edit_text(
            (
                f"⏳ Подписка {BRAND_NAME} ещё не активна.\n\n"
                "Активируй пробный период или выбери тариф."
            ),
            reply_markup=keyboards.connect_unavailable_menu(),
        )
        await callback.answer()
        return
    connect_url = await _connect_url_for(session, user=user, settings=settings)
    if not connect_url:
        await callback.answer(
            "Подписка ещё готовится, попробуй через минуту", show_alert=True
        )
        return
    text = (
        f"{format_subscription_panel(user)}\n\n"
        f"Жми «🚀 Открыть и подключить» — откроется бренд-страница {BRAND_NAME}, "
        "подписка добавится в Happ автоматически."
    )
    await callback.message.edit_text(text, reply_markup=keyboards.connect_open_menu(connect_url))
    await callback.answer()


@router.callback_query(F.data == "cabinet")
async def cabinet_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    referral_count = await referrals.count_referrals(session, user.id)
    text = (
        "👤 Кабинет\n\n"
        f"Telegram ID: {user.telegram_id}\n"
        f"Статус: {user_status(user)}\n"
        f"Доступ до: {format_date(user)}\n"
        f"📱 Лимит устройств: {user.device_limit}\n"
        f"👥 Рефералы: {referral_count}\n"
        f"🎁 Бонусные дни: {user.bonus_days}"
    )
    await callback.message.edit_text(text, reply_markup=keyboards.cabinet_menu(user))
    await callback.answer()


@router.callback_query(F.data == "invite")
async def invite_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    bot_username = (await callback.bot.get_me()).username
    await callback.message.edit_text(
        "Пригласи друга и получи бонусные дни.\n\n"
        f"Твоя ссылка:\nhttps://t.me/{bot_username}?start={user.referral_code}",
        reply_markup=keyboards.back_menu("cabinet"),
    )
    await callback.answer()


@router.callback_query(F.data == "payments_history")
async def payments_history_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    user = await ensure_user(callback, session)
    items = await payments.list_user_payments(session, user.id)
    if not items:
        text = "Пока оплат не было."
    else:
        rows = [
            f"#{payment.id}: {payment.plan.title} - {payment.final_amount}₽ - {payment.status}"
            for payment in items
        ]
        text = "История оплат\n\n" + "\n".join(rows)
    await callback.message.edit_text(text, reply_markup=keyboards.back_menu("cabinet"))
    await callback.answer()


@router.callback_query(F.data == "info")
async def info_callback(callback: CallbackQuery) -> None:
    await callback.message.edit_text(
        f"{BRAND_NAME} — простой и быстрый VPN-ускоритель без лишних настроек.\n\n"
        "Здесь — документы, инструкции и поддержка.",
        reply_markup=keyboards.info_menu(),
    )
    await callback.answer()


@router.callback_query(F.data == "documents")
async def documents_callback(callback: CallbackQuery, session: AsyncSession) -> None:
    docs = await documents.list_documents(session)
    await callback.message.edit_text(
        "Документы:",
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
    await callback.message.edit_text(f"{document.title}\n\n{document.body}", reply_markup=keyboards.back_menu("documents"))
    await callback.answer()


@router.callback_query(F.data == "support")
async def support_callback(callback: CallbackQuery) -> None:
    settings: Settings = get_settings()
    await callback.message.edit_text(f"Поддержка: {settings.support_username}", reply_markup=keyboards.back_menu("info"))
    await callback.answer()
