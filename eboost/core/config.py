from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    bot_token: str = "change-me"
    telegram_proxy: str = ""
    database_url: str = "postgresql+asyncpg://eboost:eboost@db:5432/eboost"
    backend_public_url: str = "http://localhost:8000"

    payment_provider: str = "mock"
    vpn_provider: str = "mock"
    payment_keys: str = ""
    vpn_keys: str = ""
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_base_url: str = "https://api.yookassa.ru/v3"
    yookassa_return_url: str = ""
    yookassa_receipt_email: str = ""
    yookassa_receipt_phone: str = ""
    yookassa_vat_code: int = 1
    yookassa_tax_system_code: str = ""
    yookassa_payment_mode: str = "full_payment"
    yookassa_payment_subject: str = "service"
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
    marzban_base_url: str = ""
    marzban_admin_username: str = ""
    marzban_admin_password: str = ""
    marzban_proxies: str = "vless"
    marzban_inbounds: str = ""
    marzban_data_limit_gb: int = 0
    marzban_data_limit_reset_strategy: str = "no_reset"
    happ_crypto_api_url: str = "https://crypto.happ.su/api-v2.php"
    vpn_server_specs: str = (
        "de|🇩🇪 Germany - eBooster|64.188.119.244|1|900;"
        "fi|🇫🇮 Finland - eBooster|194.113.38.23|2|900;"
        "nl|🇳🇱 Netherlands - eBooster|2.26.111.255|3|900"
    )
    server_load_check_interval_seconds: int = 300
    server_load_warning_percent: int = 70
    server_load_critical_percent: int = 85
    server_load_reset_percent: int = 60
    server_load_warning_cooldown_hours: int = 6
    server_load_critical_cooldown_hours: int = 2

    trial_days: int = 3
    ref_trial_bonus_days: int = 1
    ref_payment_bonus_days: int = 7
    ref_friends_for_bonus: int = 3
    ref_trial_daily_bonus_limit_days: int = 5
    ref_unpaid_bonus_cap_days: int = 7
    ref_paid_bonus_percent_limit: int = 50
    default_device_limit: int = 5

    support_username: str = "@eBooster_support"
    welcome_logo_path: str = "eboost/assets/ebooster_logo.png"
    connect_public_url: str = ""
    connect_token_ttl_minutes: int = 30
    happ_ios_url: str = "https://apps.apple.com/app/happ-proxy-utility/id6504287215"
    happ_android_url: str = "https://play.google.com/store/apps/details?id=com.happproxy"
    happ_macos_url: str = "https://apps.apple.com/app/happ-proxy-utility/id6504287215"
    happ_windows_url: str = "https://github.com/Happ-proxy/happ-desktop/releases/latest"
    admin_ids: str = ""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @property
    def admin_id_set(self) -> set[int]:
        ids: set[int] = set()
        for value in self.admin_ids.replace(";", ",").split(","):
            value = value.strip()
            if value:
                ids.add(int(value))
        return ids


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    legacy_ref_bonus = os.getenv("REF_БОНУС") or os.getenv("REF_BONUS")
    if legacy_ref_bonus:
        settings.ref_payment_bonus_days = int(legacy_ref_bonus)
    return settings
