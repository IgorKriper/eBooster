from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Request
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.backend.dependencies import session_dependency
from eboost.core.config import get_settings
from eboost.models import Payment
from eboost.services import payments
from eboost.services.payment.factory import get_payment_provider
from eboost.services.payment.wata_signature import verify_wata_signature
from eboost.services.vpn.factory import get_vpn_provider

router = APIRouter(prefix="/api/payments", tags=["payments"])


@router.get("/mock/pay/{payment_id}", response_class=HTMLResponse)
async def mock_pay(payment_id: int, session: AsyncSession = Depends(session_dependency)) -> str:
    settings = get_settings()
    provider = get_payment_provider(settings)
    webhook = await provider.handle_webhook({"payment_id": payment_id, "status": "succeeded"})
    try:
        payment = await payments.handle_provider_webhook(
            session,
            webhook=webhook,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return (
        "<html><body style='font-family: sans-serif; max-width: 640px; margin: 40px auto;'>"
        "<h1>Оплата прошла</h1>"
        f"<p>Платёж #{payment.id} активирован. Вернись в Telegram и нажми «Проверить оплату».</p>"
        "</body></html>"
    )


@router.post("/webhook/mock")
async def mock_webhook(payload: dict, session: AsyncSession = Depends(session_dependency)) -> dict[str, str | int]:
    settings = get_settings()
    provider = get_payment_provider(settings)
    webhook = await provider.handle_webhook(payload)
    try:
        payment = await payments.handle_provider_webhook(
            session,
            webhook=webhook,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
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
    try:
        payment = await payments.handle_provider_webhook(
            session,
            webhook=webhook,
            settings=settings,
            vpn_provider=get_vpn_provider(settings),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"status": "ok", "payment_id": payment.id}


@router.get("/{payment_id}")
async def payment_status(payment_id: int, session: AsyncSession = Depends(session_dependency)) -> dict[str, str | int]:
    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    return {"payment_id": payment.id, "status": payment.status, "final_amount": payment.final_amount}
