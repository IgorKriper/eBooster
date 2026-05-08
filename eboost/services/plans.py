from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.models import Plan
from eboost.models.plan import PLAN_KIND_DEVICE_PACK, PLAN_KIND_SUBSCRIPTION


DEFAULT_PLANS = [
    {
        "slug": "month_1",
        "title": "eBooster на 1 месяц",
        "duration_days": 30,
        "price_rub": 200,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
    },
    {
        "slug": "month_3",
        "title": "eBooster на 3 месяца",
        "duration_days": 90,
        "price_rub": 540,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
    },
    {
        "slug": "month_12",
        "title": "eBooster на 12 месяцев",
        "duration_days": 365,
        "price_rub": 1900,
        "kind": PLAN_KIND_SUBSCRIPTION,
        "bonus_devices": 0,
    },
    {
        "slug": "device_pack_1",
        "title": "eBooster +1 устройство",
        "duration_days": 0,
        "price_rub": 149,
        "kind": PLAN_KIND_DEVICE_PACK,
        "bonus_devices": 1,
    },
    {
        "slug": "device_pack_2",
        "title": "eBooster +2 устройства",
        "duration_days": 0,
        "price_rub": 249,
        "kind": PLAN_KIND_DEVICE_PACK,
        "bonus_devices": 2,
    },
    {
        "slug": "device_pack_3",
        "title": "eBooster +3 устройства",
        "duration_days": 0,
        "price_rub": 349,
        "kind": PLAN_KIND_DEVICE_PACK,
        "bonus_devices": 3,
    },
]


async def list_active_plans(session: AsyncSession) -> list[Plan]:
    result = await session.execute(
        select(Plan)
        .where(Plan.is_active.is_(True), Plan.kind == PLAN_KIND_SUBSCRIPTION)
        .order_by(Plan.price_rub)
    )
    return list(result.scalars().all())


async def list_device_packs(session: AsyncSession) -> list[Plan]:
    result = await session.execute(
        select(Plan)
        .where(Plan.is_active.is_(True), Plan.kind == PLAN_KIND_DEVICE_PACK)
        .order_by(Plan.bonus_devices)
    )
    return list(result.scalars().all())


async def get_plan(session: AsyncSession, plan_id: int) -> Plan | None:
    return await session.get(Plan, plan_id)


async def seed_plans(session: AsyncSession) -> None:
    for item in DEFAULT_PLANS:
        result = await session.execute(select(Plan).where(Plan.slug == item["slug"]))
        plan = result.scalar_one_or_none()
        if plan is None:
            session.add(Plan(**item))
        else:
            plan.title = item["title"]
            plan.duration_days = item["duration_days"]
            plan.price_rub = item["price_rub"]
            plan.kind = item["kind"]
            plan.bonus_devices = item["bonus_devices"]
            plan.is_active = True
