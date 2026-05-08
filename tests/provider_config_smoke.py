from __future__ import annotations

from eboost.core.config import Settings
from eboost.services.payment.factory import get_payment_provider
from eboost.services.payment.mock import MockPaymentProvider
from eboost.services.payment.yookassa import YooKassaPaymentProvider
from eboost.services.vpn.factory import get_vpn_provider
from eboost.services.vpn.http import HttpVpnProvider


def run() -> None:
    mock_provider = get_payment_provider(Settings(payment_provider="mock"))
    yookassa_provider = get_payment_provider(
        Settings(payment_provider="yookassa", yookassa_shop_id="shop", yookassa_secret_key="secret")
    )
    vpn_provider = get_vpn_provider(Settings(vpn_provider="http", http_vpn_base_url="https://vpn.example"))

    assert isinstance(mock_provider, MockPaymentProvider)
    assert isinstance(yookassa_provider, YooKassaPaymentProvider)
    assert isinstance(vpn_provider, HttpVpnProvider)

    nested = {"user": {"subscription": {"url": "https://sub.example"}}}
    assert vpn_provider._get_field(nested, "user.subscription.url") == "https://sub.example"

    payload = vpn_provider._render_payload(
        '{"telegram_id": "{telegram_id}", "expires_at": "{subscription_until}"}',
        default={},
        telegram_id=123,
        subscription_until="2026-05-04T00:00:00+00:00",
    )
    assert str(payload["telegram_id"]) == "123"
    assert payload["expires_at"] == "2026-05-04T00:00:00+00:00"


if __name__ == "__main__":
    run()
