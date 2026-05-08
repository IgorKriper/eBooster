from __future__ import annotations

import html
import logging
from urllib.parse import parse_qs

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from eboost.backend.dependencies import session_dependency
from eboost.bot import keyboards
from eboost.bot.texts import access as access_texts
from eboost.core.config import get_settings
from eboost.models import Payment
from eboost.models.payment import PaymentStatus
from eboost.services import payments
from eboost.services.payment.factory import get_payment_provider
from eboost.services.payment.wata_signature import verify_wata_signature
from eboost.services.vpn.factory import get_vpn_provider

router = APIRouter(prefix="/api/payments", tags=["payments"])
checkout_router = APIRouter(tags=["checkout"])
logger = logging.getLogger(__name__)


@checkout_router.get("/pay/{payment_id}", response_class=HTMLResponse)
async def checkout_page(payment_id: int, token: str, session: AsyncSession = Depends(session_dependency)) -> str:
    settings = get_settings()
    payment = await _get_payment(session, payment_id)
    if not payment or token != payments.checkout_token(settings, payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status == PaymentStatus.PAID:
        return _payment_success_html(settings)
    if payment.payment_url and payment.external_id:
        return _redirect_html(payment.payment_url)
    return _checkout_html(payment, token=token, error=None)


@checkout_router.post("/pay/{payment_id}")
async def checkout_submit(payment_id: int, token: str, request: Request, session: AsyncSession = Depends(session_dependency)):
    settings = get_settings()
    payment = await _get_payment(session, payment_id)
    if not payment or token != payments.checkout_token(settings, payment_id):
        raise HTTPException(status_code=404, detail="Payment not found")
    if payment.status == PaymentStatus.PAID:
        return HTMLResponse(_payment_success_html(settings))
    if payment.payment_url and payment.external_id:
        return RedirectResponse(payment.payment_url, status_code=303)

    body = (await request.body()).decode("utf-8")
    form = parse_qs(body)
    email = (form.get("email") or [""])[0].strip()
    if not _looks_like_email(email):
        return HTMLResponse(_checkout_html(payment, token=token, error="Проверь email для чека"), status_code=400)

    provider = get_payment_provider(settings)
    if provider.name != payment.provider:
        raise HTTPException(status_code=400, detail="Payment provider mismatch")
    try:
        await payments.start_deferred_provider_payment(
            session,
            payment=payment,
            payment_provider=provider,
            customer_email=email,
        )
    except RuntimeError as exc:
        return HTMLResponse(_checkout_html(payment, token=token, error=str(exc)), status_code=400)
    if not payment.payment_url:
        raise HTTPException(status_code=500, detail="Payment URL was not created")
    return RedirectResponse(payment.payment_url, status_code=303)


@router.get("/mock/pay/{payment_id}", response_class=HTMLResponse)
async def mock_pay(payment_id: int, session: AsyncSession = Depends(session_dependency)) -> str:
    settings = get_settings()
    provider = get_payment_provider(settings)
    webhook = await provider.handle_webhook({"payment_id": payment_id, "status": "paid"})
    was_paid = await _payment_was_paid(session, webhook.payment_id)
    try:
        payment = await payments.handle_provider_webhook(
            session,
            webhook=webhook,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _notify_payment_success(payment, settings=settings, was_paid=was_paid)
    return (
        "<html><body style='font-family: sans-serif; max-width: 640px; margin: 40px auto;'>"
        "<h1>Оплата прошла</h1>"
        f"<p>Платёж #{payment.id} активирован. Доступ откроется в Telegram автоматически.</p>"
        "</body></html>"
    )


@router.post("/webhook/mock")
async def mock_webhook(payload: dict, session: AsyncSession = Depends(session_dependency)) -> dict[str, str | int]:
    settings = get_settings()
    provider = get_payment_provider(settings)
    webhook = await provider.handle_webhook(payload)
    was_paid = await _payment_was_paid(session, webhook.payment_id)
    try:
        payment = await payments.handle_provider_webhook(
            session,
            webhook=webhook,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _notify_payment_success(payment, settings=settings, was_paid=was_paid)
    return {"status": "ok", "payment_id": payment.id}


@router.post("/webhook/wata")
async def wata_webhook(request: Request, session: AsyncSession = Depends(session_dependency)) -> dict[str, str | int]:
    settings = get_settings()
    body = await request.body()
    if settings.wata_verify_webhook_signature:
        signature = request.headers.get("X-Signature")
        if not signature or not settings.wata_webhook_public_key:
            raise HTTPException(status_code=401, detail="Missing WATA webhook signature")
        if not verify_wata_signature(
            public_key_pem=settings.wata_webhook_public_key,
            signature=signature,
            body=body,
        ):
            raise HTTPException(status_code=401, detail="Invalid WATA webhook signature")

    payload = await request.json()
    provider = get_payment_provider(settings)
    webhook = await provider.handle_webhook(payload)
    was_paid = await _payment_was_paid(session, webhook.payment_id)
    try:
        payment = await payments.handle_provider_webhook(
            session,
            webhook=webhook,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _notify_payment_success(payment, settings=settings, was_paid=was_paid)
    return {"status": "ok", "payment_id": payment.id}


@router.post("/webhook/yookassa")
async def yookassa_webhook(request: Request, session: AsyncSession = Depends(session_dependency)) -> dict[str, str | int]:
    settings = get_settings()
    payload = await request.json()
    provider = get_payment_provider(settings)
    webhook = await provider.handle_webhook(payload)
    verified_webhook = await provider.get_payment_status(external_id=webhook.external_id, payment_id=webhook.payment_id)
    if verified_webhook is None:
        raise HTTPException(status_code=401, detail="Could not verify YooKassa webhook")
    was_paid = await _payment_was_paid(session, verified_webhook.payment_id)
    try:
        payment = await payments.handle_provider_webhook(
            session,
            webhook=verified_webhook,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await _notify_payment_success(payment, settings=settings, was_paid=was_paid)
    return {"status": "ok", "payment_id": payment.id}


@router.get("/{payment_id}")
async def payment_status(payment_id: int, session: AsyncSession = Depends(session_dependency)) -> dict[str, str | int]:
    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"payment_id": payment.id, "status": payment.status, "final_amount": payment.final_amount}


async def _get_payment(session: AsyncSession, payment_id: int) -> Payment | None:
    result = await session.execute(
        select(Payment)
        .options(selectinload(Payment.plan))
        .where(Payment.id == payment_id)
    )
    return result.scalar_one_or_none()


async def _payment_was_paid(session: AsyncSession, payment_id: int) -> bool:
    payment = await session.get(Payment, payment_id)
    return bool(payment and payment.status == PaymentStatus.SUCCEEDED)


async def _notify_payment_success(payment: Payment, *, settings, was_paid: bool) -> None:
    if was_paid or payment.status != PaymentStatus.SUCCEEDED or not payment.user:
        return
    if not settings.bot_token or settings.bot_token == "change-me":
        return
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    try:
        await bot.send_message(
            payment.user.telegram_id,
            access_texts.PAYMENT_SUCCESS,
            reply_markup=keyboards.after_payment_menu(),
        )
    except Exception:
        logger.exception("Could not notify user %s about successful payment", payment.user.telegram_id)
    finally:
        await bot.session.close()


def _looks_like_email(value: str) -> bool:
    if not value or len(value) > 254 or " " in value:
        return False
    local, sep, domain = value.partition("@")
    return bool(local and sep and "." in domain and not domain.startswith(".") and not domain.endswith("."))


def _checkout_html(payment: Payment, *, token: str, error: str | None) -> str:
    plan = html.escape(payment.plan.title if payment.plan else "eBoost")
    error_html = f"<div class='error'>{html.escape(error)}</div>" if error else ""
    action = f"/pay/{payment.id}?token={html.escape(token)}"
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Оплата eBoost</title>
  <style>
    :root {{ color-scheme: light; }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: #f5f7fb;
      color: #0f1f35;
    }}
    main {{
      width: min(440px, calc(100% - 32px));
      margin: 56px auto;
      background: #fff;
      border: 1px solid #e5eaf2;
      border-radius: 18px;
      padding: 28px;
      box-shadow: 0 18px 45px rgba(15, 31, 53, .08);
    }}
    .brand {{ font-size: 26px; font-weight: 800; margin-bottom: 20px; }}
    h1 {{ font-size: 22px; line-height: 1.2; margin: 0 0 16px; }}
    .summary {{
      display: grid;
      gap: 8px;
      padding: 16px;
      border-radius: 14px;
      background: #f3f6fa;
      margin-bottom: 20px;
    }}
    .row {{ display: flex; justify-content: space-between; gap: 16px; }}
    .muted {{ color: #607086; }}
    .amount {{ font-size: 28px; font-weight: 800; }}
    label {{ display: block; font-weight: 700; margin-bottom: 8px; }}
    input {{
      width: 100%;
      height: 48px;
      border: 1px solid #cbd5e1;
      border-radius: 12px;
      padding: 0 14px;
      font-size: 16px;
      outline: none;
    }}
    input:focus {{ border-color: #2f7cf6; box-shadow: 0 0 0 4px rgba(47, 124, 246, .12); }}
    button {{
      width: 100%;
      height: 50px;
      border: 0;
      border-radius: 12px;
      background: #1769ff;
      color: #fff;
      font-size: 16px;
      font-weight: 800;
      margin-top: 16px;
      cursor: pointer;
    }}
    .hint {{ margin-top: 12px; font-size: 13px; line-height: 1.45; color: #607086; }}
    .error {{
      padding: 12px 14px;
      background: #fff0f0;
      color: #b42318;
      border-radius: 12px;
      margin-bottom: 14px;
      font-weight: 700;
    }}
  </style>
</head>
<body>
  <main>
    <div class="brand">eBoost</div>
    <h1>Оплата доступа</h1>
    <div class="summary">
      <div class="row"><span class="muted">Тариф</span><b>{plan}</b></div>
      <div class="row"><span class="muted">К оплате</span><span class="amount">{payment.final_amount} ₽</span></div>
    </div>
    {error_html}
    <form method="post" action="{action}">
      <label for="email">Email для чека</label>
      <input id="email" name="email" type="email" placeholder="pochta@example.ru" autocomplete="email" required>
      <button type="submit">Перейти к оплате</button>
      <div class="hint">Email нужен только для отправки чека после оплаты.</div>
    </form>
  </main>
</body>
</html>"""


def _redirect_html(url: str) -> str:
    safe_url = html.escape(url, quote=True)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta http-equiv="refresh" content="0; url={safe_url}">
  <title>Переход к оплате</title>
</head>
<body>
  <p>Переходим к оплате...</p>
  <p><a href="{safe_url}">Открыть оплату</a></p>
</body>
</html>"""


def _payment_success_html(settings) -> str:
    bot_url = html.escape(settings.yookassa_return_url or "https://t.me/eBooster_vpn_bot", quote=True)
    return f"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Оплата прошла</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #f5f7fb; color: #0f1f35; }}
    main {{ width: min(440px, calc(100% - 32px)); margin: 56px auto; background: #fff; border-radius: 18px; padding: 28px; box-shadow: 0 18px 45px rgba(15, 31, 53, .08); }}
    h1 {{ margin-top: 0; }}
    a {{ display: block; text-align: center; padding: 14px 16px; border-radius: 12px; background: #1769ff; color: #fff; text-decoration: none; font-weight: 800; }}
  </style>
</head>
<body>
  <main>
    <h1>Оплата прошла успешно</h1>
    <p>Доступ откроется в Telegram автоматически.</p>
    <p>Если сообщение не пришло, вернись в бот и нажми "Проверить оплату".</p>
    <a href="{bot_url}">Вернуться в eBoost</a>
  </main>
</body>
</html>"""
