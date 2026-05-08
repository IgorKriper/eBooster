from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.models import Plan
from eboost.models.plan import (
    PLAN_KIND_DEVICE_PACK,
    PLAN_KIND_SUBSCRIPTION,
    TARIFF_FAMILY,
    TARIFF_LEGACY_PLUS_5,
    TARIFF_PLUS,
    TARIFF_SOLO,
)


# TZ Executive Summary tariff catalogue.
#
# Solo / Plus / Family — три тарифа, у каждого 3 периода (1 / 3 / 12 месяцев).
# Solo дополнительно имеет 3 device-pack аддона (+1 / +2 / +3 устройства),
# которые предлагаются только пользователям на тарифе Solo.

TARIFF_TITLES: dict[str, str] = {
    TARIFF_SOLO: "Solo",
    TARIFF_PLUS: "Plus",
    TARIFF_FAMILY: "Family",
}

TARIFF_EMOJIS: dict[str, str] = {
    TARIFF_SOLO: "💎",
    TARIFF_PLUS: "🚀",
    TARIFF_FAMILY: "👑",
}

TARIFF_TAGLINES: dict[str, str] = {
    TARIFF_SOLO: "для одного человека",
    TARIFF_PLUS: "для всех своих устройств",
    TARIFF_FAMILY: "для семьи и друзей",
}

TARIFF_SLOT_LIMITS: dict[str, int] = {
    TARIFF_SOLO: 2,
    TARIFF_PLUS: 5,
    TARIFF_FAMILY: 10,
    TARIFF_LEGACY_PLUS_5: 5,
}

TARIFF_ORDER: dict[str, int] = {
    TARIFF_SOLO: 0,
    TARIFF_PLUS: 1,
    TARIFF_FAMILY: 2,
}

PERIOD_ORDER: dict[int, int] = {1: 0, 3: 1, 12: 2}

PERIOD_LABELS: dict[int, str] = {
    1: "1 месяц",
    3: "3 месяца",
    12: "12 месяцев",
}

PERIOD_SHORT_LABELS: dict[int, str] = {
    1: "1 мес",
    3: "3 мес",
    12: "12 мес",
}


DEFAULT_PLANS: list[dict[str, object]] = [
    # Solo (slot_limit=2) — переиспользуем существующие month_* строки,
    # цены уже совпадают (200/540/1900), миграция 0008 проставит метаданные.
    {
        "slug": "month_1",
        "title": "Solo · 1 мес",
        "duration_days": 30,
        "price_rub": 200,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_SOLO,
        "period_months": 1,
        "slot_limit": 2,
    },
    {
        "slug": "month_3",
        "title": "Solo · 3 мес",
        "duration_days": 90,
        "price_rub": 540,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_SOLO,
        "period_months": 3,
        "slot_limit": 2,
    },
    {
        "slug": "month_12",
        "title": "Solo · 12 мес",
        "duration_days": 365,
        "price_rub": 1900,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_SOLO,
        "period_months": 12,
        "slot_limit": 2,
    },
    # Plus (slot_limit=5).
    {
        "slug": "plus_1m",
        "title": "Plus · 1 мес",
        "duration_days": 30,
        "price_rub": 349,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_PLUS,
        "period_months": 1,
        "slot_limit": 5,
    },
    {
        "slug": "plus_3m",
        "title": "Plus · 3 мес",
        "duration_days": 90,
        "price_rub": 949,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_PLUS,
        "period_months": 3,
        "slot_limit": 5,
    },
    {
        "slug": "plus_12m",
        "title": "Plus · 12 мес",
        "duration_days": 365,
        "price_rub": 3290,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_PLUS,
        "period_months": 12,
        "slot_limit": 5,
    },
    # Family (slot_limit=10).
    {
        "slug": "family_1m",
        "title": "Family · 1 мес",
        "duration_days": 30,
        "price_rub": 590,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_FAMILY,
        "period_months": 1,
        "slot_limit": 10,
    },
    {
        "slug": "family_3m",
        "title": "Family · 3 мес",
        "duration_days": 90,
        "price_rub": 1590,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_FAMILY,
        "period_months": 3,
        "slot_limit": 10,
    },
    {
        "slug": "family_12m",
        "title": "Family · 12 мес",
        "duration_days": 365,
        "price_rub": 5490,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_FAMILY,
        "period_months": 12,
        "slot_limit": 10,
    },
    # Solo addons (only Solo gets +N devices). Reuse existing rows.
    {
        "slug": "device_pack_1",
        "title": "+1 устройство",
        "duration_days": 0,
        "price_rub": 149,
        "kind": PLAN_KIND_DEVICE_PACK,
        "bonus_devices": 1,
        "tariff_code": TARIFF_SOLO,
        "period_months": None,
        "slot_limit": 0,
    },
    {
        "slug": "device_pack_2",
        "title": "+2 устройства",
        "duration_days": 0,
        "price_rub": 249,
        "kind": PLAN_KIND_DEVICE_PACK,
        "bonus_devices": 2,
        "tariff_code": TARIFF_SOLO,
        "period_months": None,
        "slot_limit": 0,
    },
    {
        "slug": "device_pack_3",
        "title": "+3 устройства",
        "duration_days": 0,
        "price_rub": 349,
        "kind": PLAN_KIND_DEVICE_PACK,
        "bonus_devices": 3,
        "tariff_code": TARIFF_SOLO,
        "period_months": None,
        "slot_limit": 0,
    },
    # Internal legacy plan — never shown in pickers, used to keep historical
    # users on a 5-device limit as their old subscription period winds down.
    {
        "slug": "legacy_plus_5",
        "title": "Legacy (5 устройств)",
        "duration_days": 0,
        "price_rub": 0,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "tariff_code": TARIFF_LEGACY_PLUS_5,
        "period_months": None,
        "slot_limit": 5,
        "is_active": False,
    },
]


async def list_active_subscription_plans(session: AsyncSession) -> list[Plan]:
    """All active subscription rows (3 tariffs × 3 periods, 9 rows)."""
    result = await session.execute(
        select(Plan)
        .where(
            Plan.is_active.is_(True),
            Plan.kind == PLAN_KIND_SUBSCRIPTION,
            Plan.tariff_code.in_([TARIFF_SOLO, TARIFF_PLUS, TARIFF_FAMILY]),
        )
        .order_by(Plan.tariff_code, Plan.price_rub)
    )
    plans = list(result.scalars().all())
    plans.sort(
        key=lambda p: (
            TARIFF_ORDER.get(p.tariff_code or "", 99),
            PERIOD_ORDER.get(int(p.period_months or 0), 99),
        )
    )
    return plans


# Backward-compat alias for existing call sites; new code should use the
# explicit name.
async def list_active_plans(session: AsyncSession) -> list[Plan]:
    return await list_active_subscription_plans(session)


async def list_tariff_codes(session: AsyncSession) -> list[str]:
    """Tariff codes that have at least one active subscription plan."""
    plans = await list_active_subscription_plans(session)
    seen: list[str] = []
    for p in plans:
        code = p.tariff_code or ""
        if code and code not in seen:
            seen.append(code)
    return seen


async def list_plans_for_tariff(session: AsyncSession, tariff_code: str) -> list[Plan]:
    """Active subscription plans for one tariff_code, ordered by period."""
    result = await session.execute(
        select(Plan)
        .where(
            Plan.is_active.is_(True),
            Plan.kind == PLAN_KIND_SUBSCRIPTION,
            Plan.tariff_code == tariff_code,
        )
        .order_by(Plan.price_rub)
    )
    plans = list(result.scalars().all())
    plans.sort(key=lambda p: PERIOD_ORDER.get(int(p.period_months or 0), 99))
    return plans


async def list_device_packs(session: AsyncSession) -> list[Plan]:
    """Solo device-pack add-ons (+1/+2/+3), ordered by bonus count."""
    result = await session.execute(
        select(Plan)
        .where(Plan.is_active.is_(True), Plan.kind == PLAN_KIND_DEVICE_PACK)
        .order_by(Plan.bonus_devices)
    )
    return list(result.scalars().all())


async def get_plan(session: AsyncSession, plan_id: int) -> Plan | None:
    return await session.get(Plan, plan_id)


async def get_plan_by_slug(session: AsyncSession, slug: str) -> Plan | None:
    result = await session.execute(select(Plan).where(Plan.slug == slug))
    return result.scalar_one_or_none()


def slot_limit_for_tariff(tariff_code: str | None) -> int:
    return TARIFF_SLOT_LIMITS.get(tariff_code or "", 0)


def period_label(months: int | None) -> str:
    if not months:
        return ""
    return PERIOD_LABELS.get(int(months), f"{months} мес")


def period_short_label(months: int | None) -> str:
    if not months:
        return ""
    return PERIOD_SHORT_LABELS.get(int(months), f"{months} мес")


def tariff_title(tariff_code: str | None) -> str:
    return TARIFF_TITLES.get(tariff_code or "", "")


def tariff_emoji(tariff_code: str | None) -> str:
    return TARIFF_EMOJIS.get(tariff_code or "", "⚡")


def tariff_tagline(tariff_code: str | None) -> str:
    return TARIFF_TAGLINES.get(tariff_code or "", "")


async def seed_plans(session: AsyncSession) -> None:
    """Idempotent upsert of TZ catalogue. Runs on every backend boot."""
    for item in DEFAULT_PLANS:
        attrs = dict(item)
        slug = attrs.pop("slug")
        is_active = attrs.pop("is_active", True)
        result = await session.execute(select(Plan).where(Plan.slug == slug))
        plan = result.scalar_one_or_none()
        if plan is None:
            session.add(Plan(slug=slug, is_active=is_active, **attrs))
            continue
        for key, value in attrs.items():
            setattr(plan, key, value)
        plan.is_active = is_active
