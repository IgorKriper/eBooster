# Happ Integration Notes

Happ is treated as the client app in eBoost UX. The backend still needs a VPN/Proxy provider or panel that creates users and returns a subscription URL compatible with Happ.

Current MVP:

- `MockVpnProvider` creates stable mock user IDs.
- It returns a fake subscription URL for Telegram UX testing.
- The bot mentions Happ only in device instructions.

Real integration target:

1. Choose a panel/provider that can generate subscription URLs Happ accepts.
2. Implement `eboost.services.vpn.base.VpnProvider`.
3. Register it in `eboost.services.vpn.factory.get_vpn_provider`.
4. Keep bot handlers unchanged.

The project also includes a configurable HTTP adapter:

```env
VPN_PROVIDER=http
HTTP_VPN_BASE_URL=https://your-panel.example
HTTP_VPN_TOKEN=
HTTP_VPN_CREATE_PATH=/users
HTTP_VPN_EXTEND_PATH=/users/{vpn_user_id}/extend
HTTP_VPN_DISABLE_PATH=/users/{vpn_user_id}/disable
HTTP_VPN_SUBSCRIPTION_PATH=/users/{vpn_user_id}/subscription
HTTP_VPN_USER_ID_FIELD=id
HTTP_VPN_SUBSCRIPTION_URL_FIELD=subscription_url
```

If your panel uses different JSON payloads, set templates:

```env
HTTP_VPN_CREATE_PAYLOAD={"telegram_id":"{telegram_id}","expires_at":"{subscription_until}"}
HTTP_VPN_EXTEND_PAYLOAD={"expires_at":"{subscription_until}"}
```

Response fields support dot paths, for example:

```env
HTTP_VPN_USER_ID_FIELD=user.id
HTTP_VPN_SUBSCRIPTION_URL_FIELD=user.subscription.url
```

The required provider methods are:

```text
create_user
extend_user
disable_user
get_subscription_url
```
