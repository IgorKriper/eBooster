from __future__ import annotations

import aiohttp
from decimal import Decimal, InvalidOperation

from eboost.core.config import Settings
from eboost.models.payment import PaymentStatus
from eboost.services.payment.base import PaymentCreateRequest, PaymentCreateResult, PaymentProvider, PaymentWebhookResult


class WataPaymentProvider(PaymentProvider):
    name = "wata"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_payment(self, request: PaymentCreateRequest) -> PaymentCreateResult:
        if not self.settings.wata_access_token:
            raise RuntimeError("Set WATA_ACCESS_TOKEN to use WATA payments")

        payload: dict[str, object] = {
            "type": "OneTime",
            "amount": float(request.amount_rub),
            "currency": "RUB",
            "description": request.description,
            "orderId": str(request.payment_id),
        }
        if self.settings.wata_success_redirect_url:
            payload["successRedirectUrl"] = self.settings.wata_success_redirect_url
        if self.settings.wata_fail_redirect_url:
            payload["failRedirectUrl"] = self.settings.wata_fail_redirect_url

        headers = {
            "Authorization": f"Bearer {self.settings.wata_access_token}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.wata_base_url.rstrip('/')}/links/"
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.post(url, json=payload, timeout=60) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"WATA create payment failed: {response.status} {data}")

        payment_link_id = str(data["id"])
        payment_url = str(data["url"])
        return PaymentCreateResult(external_id=payment_link_id, payment_url=payment_url)

    async def handle_webhook(self, payload: dict) -> PaymentWebhookResult:
        order_id = payload.get("orderId")
        if order_id is None:
            raise ValueError("WATA webhook payload does not contain orderId")

        transaction_status = str(payload.get("transactionStatus") or payload.get("status") or "")
        status = {
            "Paid": PaymentStatus.SUCCEEDED,
            "Declined": PaymentStatus.FAILED,
            "Created": PaymentStatus.PENDING,
            "Pending": PaymentStatus.PENDING,
        }.get(transaction_status, PaymentStatus.PENDING)

        external_id = str(payload.get("paymentLinkId") or payload.get("id") or payload.get("transactionId") or order_id)
        amount_rub = self._amount_to_int(payload.get("amount"))
        currency = str(payload.get("currency") or "") or None
        return PaymentWebhookResult(
            payment_id=int(order_id),
            external_id=external_id,
            status=status,
            amount_rub=amount_rub,
            currency=currency,
        )

    def _amount_to_int(self, amount: object) -> int | None:
        if amount is None:
            return None
        try:
            value = Decimal(str(amount))
        except (InvalidOperation, ValueError):
            return None
        if value != value.to_integral_value():
            return None
        return int(value)
