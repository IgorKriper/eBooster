from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.models import Plan
from eboost.models.plan import PLAN_KIND_DEVICE_PACK, PLAN_KIND_SUBSCRIPTION


# TZ v2 tariff catalogue.
# Solo / Plus / Family share a 30-day period; only the device limit differs.
# Solo gets a single device-pack add-on (+1 slot for 99₽ default per TZ).
SOLO_SLUG = "solo"
PLUS_SLUG = "plus"
FAMILY_SLUG = "family"
SOLO_ADDON_SLUG = "solo_addon_1"

TARIFF_TITLES: dict[str, str] = {
    SOLO_SLUG: "Solo",
    PLUS_SLUG: "Plus",
    FAMILY_SLUG: "Family",
}

TARIFF_EMOJIS: dict[str, str] = {
    SOLO_SLUG: "⚡",
    PLUS_SLUG: "🚀",
    FAMILY_SLUG: "👑",
}


DEFAULT_PLANS: list[dict[str, object]] = [
    {
        "slug": SOLO_SLUG,
        "title": "Solo",
        "duration_days": 30,
        "price_rub": 200,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "slot_devices": 2,
    },
    {
        "slug": PLUS_SLUG,
        "title": "Plus",
        "duration_days": 30,
        "price_rub": 349,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "slot_devices": 5,
    },
    {
        "slug": FAMILY_SLUG,
        "title": "Family",
        "duration_days": 30,
        "price_rub": 590,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
        "slot_devices": 10,
    },
    {
        "slug": SOLO_ADDON_SLUG,
        "title": "+1 устройство",
        "duration_days": 0,
        "price_rub": 99,
        "kind": PLAN_KIND_DEVICE_PACK,
        "bonus_devices": 1,
        "slot_devices": 0,
    },
]

# Slugs of legacy plans kept in DB for historical Payment refs but hidden from
# users. seed_plans() force-deactivates them on every boot.
LEGACY_SLUGS: tuple[str, ...] = (
    "month_1",
    "month_3",
    "month_12",
    "device_pack_1",
    "device_pack_2",
    "device_pack_3",
)

_TARIFF_SORT: dict[str, int] = {SOLO_SLUG: 0, PLUS_SLUG: 1, FAMILY_SLUG: 2}


async def list_active_plans(session: AsyncSession) -> list[Plan]:
    """Return active subscription tariffs in canonical Solo/Plus/Family order."""
    result = await session.execute(
        select(Plan)
        .where(Plan.is_active.is_(True), Plan.kind == PLAN_KIND_SUBSCRIPTION)
        .order_by(Plan.price_rub)
    )
    plans = list(result.scalars().all())
    plans.sort(key=lambda p: (_TARIFF_SORT.get(p.slug, 99), p.price_rub))
    return plans


async def list_device_packs(session: AsyncSession) -> list[Plan]:
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


async def seed_plans(session: AsyncSession) -> None:
    # Upsert TZ v2 catalogue.
    for item in DEFAULT_PLANS:
        result = await session.execute(select(Plan).where(Plan.slug == item["slug"]))
        plan = result.scalar_one_or_none()
        if plan is None:
            session.add(Plan(**item))
        else:
            plan.title = item["title"]  # type: ignore[assignment]
            plan.duration_days = item["duration_days"]  # type: ignore[assignment]
            plan.price_rub = item["price_rub"]  # type: ignore[assignment]
            plan.kind = item["kind"]  # type: ignore[assignment]
            plan.bonus_devices = item["bonus_devices"]  # type: ignore[assignment]
            plan.slot_devices = item["slot_devices"]  # type: ignore[assignment]
            plan.is_active = True

    # Deactivate legacy plans, but keep rows so historical payments still resolve.
    if LEGACY_SLUGS:
        await session.execute(
            update(Plan).where(Plan.slug.in_(LEGACY_SLUGS)).values(is_active=False)
        )
