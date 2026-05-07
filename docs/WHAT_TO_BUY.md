# What You Need To Buy Or Create

For the first real launch you need:

1. VPS for the eBoost bot/backend/database.
   - Ubuntu 22.04 or 24.04.
   - 2 vCPU, 2 GB RAM minimum.
   - 20-40 GB SSD.
   - Public IPv4.

2. Domain or subdomain for the backend.
   - Example: `api.your-domain.com`.
   - DNS `A` record must point to the VPS IP.
   - This is needed for WATA webhooks over HTTPS.

3. WATA merchant account.
   - Access token.
   - Webhook URL: `https://api.your-domain.com/api/payments/webhook/wata`.
   - Optional webhook public key for signature verification.

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
WATA_ACCESS_TOKEN=
HTTP_VPN_BASE_URL=
HTTP_VPN_TOKEN=
ADMIN_IDS=
SUPPORT_USERNAME=
```

## Recommended Order

1. Buy VPS.
2. Point domain/subdomain to VPS IP.
3. Install Docker on VPS.
4. Deploy eBoost with mock VPN and mock payment first.
5. Switch payment to WATA.
6. Switch VPN to the real panel.
7. Run a full Telegram purchase test.
