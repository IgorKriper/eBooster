# eBoost Production Checklist

This MVP is already wired through provider interfaces. To replace mocks, collect the values below and add provider adapters without changing bot handlers.

## Required Decisions

- VPN/Proxy provider or panel that can issue Happ-compatible subscription links: Marzban, 3x-ui, Hiddify panel, custom API, or another service.
- Payment provider: YooKassa is the preferred real-provider target in this codebase.
- Public HTTPS backend URL for payment webhooks.
- Production PostgreSQL connection string.
- Telegram bot token.
- Admin Telegram IDs.
- Support contact.

## VPN Adapter Contract

Implement `eboost.services.vpn.base.VpnProvider`:

```text
create_user
extend_user
disable_user
get_subscription_url
```

Then register the adapter in `eboost.services.vpn.factory.get_vpn_provider`.

## Payment Adapter Contract

Implement `eboost.services.payment.base.PaymentProvider`:

```text
create_payment
handle_webhook
get_payment_status (optional, used by the bot payment check button)
```

Then register the adapter in `eboost.services.payment.factory.get_payment_provider`.

## YooKassa Payments

Set:

```env
PAYMENT_PROVIDER=yookassa
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_RETURN_URL=https://t.me/your_bot
BACKEND_PUBLIC_URL=https://your-server-ip
```

Configure the YooKassa webhook URL in the merchant dashboard:

```text
https://your-server-ip/api/payments/webhook/yookassa
```

The adapter stores the internal payment ID in YooKassa `metadata.payment_id`. The webhook handler and the bot payment check button use that metadata to activate the payment and extend access.

The service layer already persists:

- payment status
- original amount
- discount percent
- final amount
- promo code usage
- subscription extension
- referral bonuses

## Environment To Fill

```env
BOT_TOKEN=
DATABASE_URL=
BACKEND_PUBLIC_URL=https://your-domain.example

PAYMENT_PROVIDER=yookassa
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_RETURN_URL=https://t.me/your_bot

VPN_PROVIDER=http
VPN_KEYS=
HTTP_VPN_BASE_URL=
HTTP_VPN_TOKEN=
HTTP_VPN_CREATE_PATH=/users
HTTP_VPN_EXTEND_PATH=/users/{vpn_user_id}/extend
HTTP_VPN_DISABLE_PATH=/users/{vpn_user_id}/disable
HTTP_VPN_SUBSCRIPTION_PATH=/users/{vpn_user_id}/subscription
HTTP_VPN_USER_ID_FIELD=id
HTTP_VPN_SUBSCRIPTION_URL_FIELD=subscription_url

TRIAL_DAYS=3
REF_TRIAL_BONUS_DAYS=1
REF_PAYMENT_BONUS_DAYS=7
SUPPORT_USERNAME=@eBoost_support
ADMIN_IDS=
```

## Before Launch

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_all_local.ps1
```

Then verify in Telegram:

```text
/start
trial activation
plan selection
promo code
payment completion
cabinet
payment history
device instructions
```
