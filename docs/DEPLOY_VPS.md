# Deploy eBoost On A VPS

This guide assumes Ubuntu 22.04 or 24.04.

## 1. Install Docker

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Log out and log in again.

## 2. Upload Project

Clone or copy this project to the VPS:

```bash
cd /opt
sudo mkdir -p eboost
sudo chown $USER:$USER eboost
cd eboost
```

Copy project files into `/opt/eboost`.

## 3. Configure Env

```bash
cp .env.production.example .env
nano .env
```

Minimum production values:

```env
BOT_TOKEN=
BACKEND_PUBLIC_URL=https://api.example.com
CADDY_DOMAIN=api.example.com
CADDY_EMAIL=admin@example.com
POSTGRES_PASSWORD=
ADMIN_IDS=
```

Start with mocks:

```env
PAYMENT_PROVIDER=mock
VPN_PROVIDER=mock
```

Then switch to real services after the bot is alive.

## 4. Start

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Check:

```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f backend
docker compose -f docker-compose.prod.yml logs -f bot
```

Health:

```bash
curl https://api.example.com/health
```

## 5. Public IP Mode Without Domain

For YooKassa without a domain, use HTTPS on the VPS IP with Caddy's internal certificate:

```bash
cp deploy/Caddyfile.ip-https deploy/Caddyfile
```

Set:

```env
CADDY_DOMAIN=
SERVER_IP=YOUR_SERVER_IP
BACKEND_PUBLIC_URL=https://YOUR_SERVER_IP
```

Restart Caddy:

```bash
docker compose -f docker-compose.prod.yml up -d caddy
```

Webhook URL:

```text
https://YOUR_SERVER_IP/api/payments/webhook/yookassa
```

## 6. YooKassa Webhook

In YooKassa dashboard set:

```text
https://api.example.com/api/payments/webhook/yookassa
```

Or, in public IP mode:

```text
https://YOUR_SERVER_IP/api/payments/webhook/yookassa
```

Then set:

```env
PAYMENT_PROVIDER=yookassa
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
YOOKASSA_RETURN_URL=https://t.me/your_bot
```

Restart:

```bash
docker compose -f docker-compose.prod.yml up -d
```

## 7. Real VPN Provider

Set:

```env
VPN_PROVIDER=http
HTTP_VPN_BASE_URL=
HTTP_VPN_TOKEN=
HTTP_VPN_CREATE_PATH=
HTTP_VPN_EXTEND_PATH=
HTTP_VPN_DISABLE_PATH=
HTTP_VPN_SUBSCRIPTION_PATH=
HTTP_VPN_USER_ID_FIELD=
HTTP_VPN_SUBSCRIPTION_URL_FIELD=
```

Restart and test trial activation.
