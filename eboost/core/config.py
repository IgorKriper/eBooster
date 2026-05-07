from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

from eboost.core.branding import (
    BOT_LONG_DESCRIPTION,
    BOT_SHORT_DESCRIPTION,
    SUPPORT_USERNAME_DEFAULT,
    WELCOME_LOGO_PATH,
)


class Settings(BaseSettings):
    bot_token: str = "change-me"
    telegram_proxy: str = ""
    database_url: str = "postgresql+asyncpg://eboost:eboost@db:5432/eboost"
    backend_public_url: str = "http://localhost:8000"
    connect_public_url: str = ""

    payment_provider: str = "mock"
    vpn_provider: str = "mock"
    payment_keys: str = ""
    vpn_keys: str = ""
    wata_access_token: str = ""
    wata_base_url: str = "https://api.wata.pro/api/h2h"
    wata_success_redirect_url: str = ""
    wata_fail_redirect_url: str = ""
    wata_verify_webhook_signature: bool = False
    wata_webhook_public_key: str = ""
    http_vpn_base_url: str = ""
    http_vpn_token: str = ""
    http_vpn_create_path: str = "/users"
    http_vpn_extend_path: str = "/users/{vpn_user_id}/extend"
    http_vpn_disable_path: str = "/users/{vpn_user_id}/disable"
    http_vpn_subscription_path: str = "/users/{vpn_user_id}/subscription"
    http_vpn_create_payload: str = ""
    http_vpn_extend_payload: str = ""
    http_vpn_user_id_field: str = "id"
    http_vpn_subscription_url_field: str = "subscription_url"

    trial_days: int = 3
    ref_trial_bonus_days: int = 1
    ref_payment_bonus_days: int = 7

    support_username: str = SUPPORT_USERNAME_DEFAULT
    admin_ids: str = ""

    welcome_logo_path: str = str(WELCOME_LOGO_PATH)
    bot_short_description: str = BOT_SHORT_DESCRIPTION
    bot_long_description: str = BOT_LONG_DESCRIPTION
    auto_set_bot_descriptions: bool = True

    happ_ios_url: str = "https://apps.apple.com/app/happ-proxy-utility/id6504287215"
    happ_android_url: str = "https://play.google.com/store/apps/details?id=com.happproxy"
    happ_macos_url: str = "https://apps.apple.com/app/happ-proxy-utility/id6504287215"
    happ_windows_url: str = "https://github.com/Happ-proxy/happ-desktop/releases/latest"

    default_device_limit: int = 4
    connect_token_ttl_minutes: int = 30

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_id_set(self) -> set[int]:
        ids: set[int] = set()
        for value in self.admin_ids.replace(";", ",").split(","):
            value = value.strip()
            if value:
                ids.add(int(value))
        return ids

    @property
    def effective_connect_public_url(self) -> str:
        return (self.connect_public_url or self.backend_public_url).rstrip("/")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    legacy_ref_bonus = os.getenv("REF_БОНУС") or os.getenv("REF_BONUS")
    if legacy_ref_bonus:
        settings.ref_payment_bonus_days = int(legacy_ref_bonus)
    return settings
