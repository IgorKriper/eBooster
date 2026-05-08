# eBoost MVP

eBoost is a Telegram bot plus FastAPI backend for selling simple VPN/Proxy access positioned as an internet booster. This MVP uses mock VPN and mock payments first, while keeping both integrations behind provider interfaces so real services can be added without rewriting bot or subscription logic.

## What Is Included

- Telegram bot on aiogram 3.x.
- FastAPI backend with mock payment webhook.
- PostgreSQL schema with SQLAlchemy models and Alembic migration.
- Mock VPN provider with `create_user`, `extend_user`, `disable_user`, `get_subscription_url`.
- Mock payment provider with `create_payment` and `handle_webhook`.
- YooKassa payment adapter with real payment-link creation, webhook handling, and manual status checks.
- WATA payment adapter remains available as an optional legacy adapter.
- Trial access for 3 days, once per user.
- Plans: 1 month, 3 months, 12 months.
- Promo codes with first-payment-only rules and stored original/discount/final amounts.
- Referral bonuses: +1 day for trial activation, +7 days after payment.
- Cabinet, payment history, documents, support, and basic admin commands.
- Docker Compose for backend, bot, and PostgreSQL.

## Project Structure

```text
eboost/
  api/              Compatibility exports for API routers
  backend/          FastAPI app and HTTP routes
  bot/              aiogram bot, routers, keyboards, FSM
  core/             Settings and shared utilities
  db/               Async SQLAlchemy engine/session
  models/           SQLAlchemy models
  services/         Business logic and provider abstractions
migrations/         Alembic migrations
docker-compose.yml
Dockerfile
requirements.txt
```

## Quick Start

1. Copy environment variables:

```bash
cp .env.example .env
```

2. Put a real Telegram token into `.env`:

```env
BOT_TOKEN=123456:telegram-token
```

3. Start the project:

```bash
docker compose up --build
```

The backend will run Alembic migrations and start on `http://localhost:8000`. The bot starts after the backend healthcheck passes.

For VPS launch, see [docs/DEPLOY_VPS.md](docs/DEPLOY_VPS.md).
For purchase/account checklist, see [docs/WHAT_TO_BUY.md](docs/WHAT_TO_BUY.md).

## Local Smoke Test

For a quick business-flow check without PostgreSQL, install dev dependencies and run:

```bash
pip install -r requirements-dev.txt
python tests/smoke_flow.py
```

The smoke test uses in-memory SQLite and checks: default seed data, referral link, trial activation, promo code, mock payment completion, subscription extension, mock VPN link, and referral bonus days.

On Windows in this workspace, after the portable Python setup, you can also run:

```powershell
.\scripts\run_smoke_local.ps1
```

If PowerShell blocks local scripts, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\setup_local.ps1
powershell -ExecutionPolicy Bypass -File .\scripts\run_smoke_local.ps1
```

## Local Backend Without Docker

If Docker Desktop is not available yet, run the backend locally with SQLite:

```powershell
.\scripts\run_backend_local.ps1
```

Or, if scripts are blocked:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_backend_local.ps1
```

Then open:

```text
http://localhost:8000/health
```

This mode is for local verification only. Production/staging should use PostgreSQL through `docker-compose.yml`.

To verify the backend mock payment endpoint end to end without Docker:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_backend_mock_payment_local.ps1
```

To run all local checks:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\check_all_local.ps1
```

## Local Bot Without Docker

Set `BOT_TOKEN` in the current PowerShell session or in `.env`, then run:

```powershell
$env:BOT_TOKEN = "123456:telegram-token"
powershell -ExecutionPolicy Bypass -File .\scripts\run_bot_local.ps1
```

Run the backend in another PowerShell window if you want mock payment links to open locally.

If direct access to `api.telegram.org:443` is blocked, set an HTTP proxy before launching the bot:

```powershell
$env:TELEGRAM_PROXY = "http://127.0.0.1:8080"
powershell -ExecutionPolicy Bypass -File .\scripts\run_bot_local.ps1
```

## Mock Payment Flow

1. User selects a plan in Telegram.
2. Bot creates a pending payment through `MockPaymentProvider`.
3. Payment URL points to:

```text
http://localhost:8000/api/payments/mock/pay/{payment_id}
```

4. Opening this URL simulates a successful webhook.
5. Backend marks payment as succeeded, extends subscription, syncs mock VPN access, applies promo usage, and awards referral bonus.
6. User returns to Telegram and presses `Проверить оплату`.

## Default Data

On startup the app seeds:

- `eBoost на 1 месяц` - 199 RUB.
- `eBoost на 3 месяца` - 499 RUB.
- `eBoost на 12 месяцев` - 1490 RUB.
- Documents: privacy policy, terms, refunds.
- Promo code `WELCOME30` for 30% off the first payment.

## Environment

```env
BOT_TOKEN=change-me
TELEGRAM_PROXY=
DATABASE_URL=postgresql+asyncpg://eboost:eboost@db:5432/eboost
BACKEND_PUBLIC_URL=http://localhost:8000

PAYMENT_PROVIDER=mock
VPN_PROVIDER=mock
PAYMENT_KEYS=
VPN_KEYS=
WATA_ACCESS_TOKEN=
WATA_BASE_URL=https://api.wata.pro/api/h2h
WATA_SUCCESS_REDIRECT_URL=
WATA_FAIL_REDIRECT_URL=
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_BASE_URL=https://api.yookassa.ru/v3
YOOKASSA_RETURN_URL=https://t.me/your_bot

TRIAL_DAYS=3
REF_TRIAL_BONUS_DAYS=1
REF_PAYMENT_BONUS_DAYS=7
# Optional legacy alias from the original brief. If set, it maps to payment referral bonus.
REF_BONUS=

SUPPORT_USERNAME=@eBoost_support
ADMIN_IDS=123456789
```

## Replacing Mock Providers

Add a new adapter that implements:

- `eboost.services.vpn.base.VpnProvider`
- `eboost.services.payment.base.PaymentProvider`

Then register it in:

- `eboost.services.vpn.factory.get_vpn_provider`
- `eboost.services.payment.factory.get_payment_provider`

The bot, backend, subscription service, trial service, and payment service do not need to change.

See [docs/PRODUCTION.md](docs/PRODUCTION.md) for the launch checklist and integration inputs.
See [docs/HAPP.md](docs/HAPP.md) for Happ-specific integration notes.

For many VPN panels you can start with the generic HTTP adapter:

```env
VPN_PROVIDER=http
HTTP_VPN_BASE_URL=https://your-panel.example
HTTP_VPN_TOKEN=your-token
HTTP_VPN_USER_ID_FIELD=id
HTTP_VPN_SUBSCRIPTION_URL_FIELD=subscription_url
```

## YooKassa

To switch from mock payments to YooKassa:

```env
PAYMENT_PROVIDER=yookassa
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_SECRET_KEY=your-secret-key
YOOKASSA_RETURN_URL=https://t.me/your_bot
BACKEND_PUBLIC_URL=http://your-server-ip
```

Then configure this webhook URL in YooKassa:

```text
http://your-server-ip/api/payments/webhook/yookassa
```

The bot also checks payment status through the YooKassa API when the user presses the payment check button.

## WATA

To switch from mock payments to WATA:

```env
PAYMENT_PROVIDER=wata
WATA_ACCESS_TOKEN=your-token
BACKEND_PUBLIC_URL=https://your-domain.example
```

Then configure this webhook URL in WATA:

```text
https://your-domain.example/api/payments/webhook/wata
```

WATA payment buttons must use public HTTPS URLs. Localhost is intentionally handled by the mock callback flow instead.

## Admin Commands

Set `ADMIN_IDS` to comma-separated Telegram IDs.

```text
/admin
/stats
/user <telegram_id>
/give <telegram_id> <days>
/disable <telegram_id>
/promos
/promo <code> <discount_percent> [max_uses]
/promo_off <code>
/broadcast <text>
```

## Notes

- The product text avoids technical wording in the user-facing flow.
- Happ appears only in connection instructions.
- The mock subscription URL is intentionally generated by the VPN provider layer, not by bot handlers.
