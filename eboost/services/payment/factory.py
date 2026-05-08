from __future__ import annotations

from eboost.core.config import Settings
from eboost.services.payment.base import PaymentProvider
from eboost.services.payment.mock import MockPaymentProvider
from eboost.services.payment.wata import WataPaymentProvider
from eboost.services.payment.yookassa import YooKassaPaymentProvider


def get_payment_provider(settings: Settings) -> PaymentProvider:
    if settings.payment_provider == "mock":
        return MockPaymentProvider(settings)
    if settings.payment_provider == "wata":
        return WataPaymentProvider(settings)
    if settings.payment_provider == "yookassa":
        return YooKassaPaymentProvider(settings)
    raise ValueError(f"Unsupported payment provider: {settings.payment_provider}")
