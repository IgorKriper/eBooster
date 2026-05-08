from __future__ import annotations

from decimal import Decimal, InvalidOperation
from uuid import uuid4

import aiohttp

from eboost.core.config import Settings
from eboost.models.payment import PaymentStatus
from eboost.services.payment.base import PaymentCreateRequest, PaymentCreateResult, PaymentProvider, PaymentWebhookResult


class YooKassaPaymentProvider(PaymentProvider):
    name = "yookassa"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_payment(self, request: PaymentCreateRequest) -> PaymentCreateResult:
        if not self.settings.yookassa_shop_id or not self.settings.yookassa_secret_key:
            raise RuntimeError("Set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY to use YooKassa payments")

        payload: dict[str, object] = {
            "amount": {
                "value": f"{request.amount_rub:.2f}",
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "locale": "ru_RU",
                "return_url": self.settings.yookassa_return_url or self.settings.backend_public_url,
            },
            "description": f"eBooster: {request.description}",
            "metadata": {
                "payment_id": str(request.payment_id),
                "user_id": str(request.user_id),
            },
        }
        payload["receipt"] = self._receipt_payload(request)
        headers = {
            "Idempotence-Key": f"eboost-payment-{request.payment_id}-{uuid4()}",
            "Content-Type": "application/json",
        }
        url = f"{self.settings.yookassa_base_url.rstrip('/')}/payments"
        auth = aiohttp.BasicAuth(self.settings.yookassa_shop_id, self.settings.yookassa_secret_key)
        async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
            async with session.post(url, json=payload, timeout=60) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"YooKassa create payment failed: {response.status} {data}")

        confirmation = data.get("confirmation") or {}
        payment_url = confirmation.get("confirmation_url")
        if not payment_url:
            raise RuntimeError(f"YooKassa response does not contain confirmation_url: {data}")
        return PaymentCreateResult(external_id=str(data["id"]), payment_url=str(payment_url))

    async def handle_webhook(self, payload: dict) -> PaymentWebhookResult:
        payment_object = payload.get("object") if "object" in payload else payload
        if not isinstance(payment_object, dict):
            raise ValueError("YooKassa webhook payload does not contain payment object")
        return self._result_from_payment_object(payment_object)

    async def get_payment_status(self, *, external_id: str, payment_id: int) -> PaymentWebhookResult | None:
        if not self.settings.yookassa_shop_id or not self.settings.yookassa_secret_key:
            raise RuntimeError("Set YOOKASSA_SHOP_ID and YOOKASSA_SECRET_KEY to use YooKassa payments")

        url = f"{self.settings.yookassa_base_url.rstrip('/')}/payments/{external_id}"
        auth = aiohttp.BasicAuth(self.settings.yookassa_shop_id, self.settings.yookassa_secret_key)
        async with aiohttp.ClientSession(auth=auth) as session:
            async with session.get(url, timeout=60) as response:
                data = await response.json(content_type=None)
                if response.status >= 400:
                    raise RuntimeError(f"YooKassa get payment failed: {response.status} {data}")

        result = self._result_from_payment_object(data)
        if result.payment_id != payment_id:
            raise ValueError("YooKassa payment metadata mismatch")
        return result

    def _result_from_payment_object(self, payment: dict) -> PaymentWebhookResult:
        metadata = payment.get("metadata") or {}
        payment_id = metadata.get("payment_id") or metadata.get("order_id")
        if payment_id is None:
            raise ValueError("YooKassa payment object does not contain metadata.payment_id")

        status = self._map_status(str(payment.get("status") or ""), bool(payment.get("paid")))
        amount = payment.get("amount") or {}
        return PaymentWebhookResult(
            payment_id=int(payment_id),
            external_id=str(payment.get("id") or payment_id),
            status=status,
            amount_rub=self._amount_to_int(amount.get("value")),
            currency=str(amount.get("currency") or "") or None,
        )

    def _map_status(self, status: str, paid: bool) -> str:
        if status == "succeeded" and paid:
            return PaymentStatus.PAID
        if status == "canceled":
            return PaymentStatus.CANCELLED
        return PaymentStatus.PENDING

    def _receipt_payload(self, request: PaymentCreateRequest) -> dict[str, object]:
        customer: dict[str, str] = {}
        email = (request.customer_email or self.settings.yookassa_receipt_email).strip()
        phone = self.settings.yookassa_receipt_phone.strip()
        if email:
            customer["email"] = email
        elif phone:
            customer["phone"] = phone
        else:
            raise RuntimeError("YooKassa receipt customer email or phone is required")

        receipt: dict[str, object] = {
            "customer": customer,
            "items": [
                {
                    "description": self._receipt_description(request.description),
                    "quantity": "1.00",
                    "amount": {
                        "value": f"{request.amount_rub:.2f}",
                        "currency": "RUB",
                    },
                    "vat_code": self.settings.yookassa_vat_code,
                    "payment_mode": self.settings.yookassa_payment_mode,
                    "payment_subject": self.settings.yookassa_payment_subject,
                }
            ],
        }
        tax_system_code = self.settings.yookassa_tax_system_code.strip()
        if tax_system_code:
            receipt["tax_system_code"] = int(tax_system_code)
        return receipt

    def _receipt_description(self, description: str) -> str:
        value = f"eBooster: {description}".strip()
        return value[:128] or "eBooster"

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
