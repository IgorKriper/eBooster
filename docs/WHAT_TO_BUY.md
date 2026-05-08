# What You Need To Buy Or Create

For the first real launch you need:

1. VPS for the eBoost bot/backend/database.
   - Ubuntu 22.04 or 24.04.
   - 2 vCPU, 2 GB RAM minimum.
   - 20-40 GB SSD.
   - Public IPv4.

2. Domain or subdomain for the backend, optional if your payment provider accepts public IP webhooks.
   - Example: `api.your-domain.com`.
   - DNS `A` record must point to the VPS IP.
   - This is optional for MVP: YooKassa requires HTTPS webhooks, but Caddy can serve HTTPS directly on the VPS IP with an internal certificate.

3. YooKassa merchant account.
   - Shop ID.
   - Secret key.
   - Webhook URL: `https://api.your-domain.com/api/payments/webhook/yookassa`.

4. VPN/Proxy panel or provider that can issue Happ-compatible subscription links.
   - API base URL.
   - API token.
   - Endpoint docs or example requests/responses.

5. Telegram bot token.
   - You already created one via BotFather.

6. Support username.
   - Example: `@eBoost_support`.

Send these values to the deployment environment, not into public chat:

```env
BOT_TOKEN=
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
HTTP_VPN_BASE_URL=
HTTP_VPN_TOKEN=
ADMIN_IDS=
SUPPORT_USERNAME=
```

## Recommended Order

1. Buy VPS.
2. Install Docker on VPS.
3. Deploy eBoost with mock VPN and mock payment first.
4. If using a domain, point domain/subdomain to VPS IP.
5. If skipping domain, use public IP mode.
6. Switch payment to YooKassa.
7. Switch VPN to the real panel.
8. Run a full Telegram purchase test.
