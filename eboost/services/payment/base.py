from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class PaymentCreateRequest:
    payment_id: int
    user_id: int
    amount_rub: int
    description: str
    customer_email: str | None = None


@dataclass(frozen=True)
class PaymentCreateResult:
    external_id: str
    payment_url: str


@dataclass(frozen=True)
class PaymentWebhookResult:
    payment_id: int
    external_id: str
    status: str
    amount_rub: int | None = None
    currency: str | None = None


class PaymentProvider(ABC):
    name: str

    @abstractmethod
    async def create_payment(self, request: PaymentCreateRequest) -> PaymentCreateResult:
        raise NotImplementedError

    @abstractmethod
    async def handle_webhook(self, payload: dict) -> PaymentWebhookResult:
        raise NotImplementedError

    async def get_payment_status(self, *, external_id: str, payment_id: int) -> PaymentWebhookResult | None:
        return None
