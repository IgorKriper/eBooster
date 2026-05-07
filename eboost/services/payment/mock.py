from __future__ import annotations

from eboost.core.config import Settings
from eboost.models.payment import PaymentStatus
from eboost.services.payment.base import PaymentCreateRequest, PaymentCreateResult, PaymentProvider, PaymentWebhookResult


class MockPaymentProvider(PaymentProvider):
    name = "mock"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_payment(self, request: PaymentCreateRequest) -> PaymentCreateResult:
        external_id = f"mock-payment-{request.payment_id}"
        payment_url = f"{self.settings.backend_public_url}/api/payments/mock/pay/{request.payment_id}"
        return PaymentCreateResult(external_id=external_id, payment_url=payment_url)

    async def handle_webhook(self, payload: dict) -> PaymentWebhookResult:
        payment_id = int(payload["payment_id"])
        status = str(payload.get("status", PaymentStatus.SUCCEEDED))
        return PaymentWebhookResult(payment_id=payment_id, external_id=f"mock-payment-{payment_id}", status=status)
