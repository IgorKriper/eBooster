from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.models import Plan


DEFAULT_PLANS = [
    {"slug": "month_1", "title": "eBoost на 1 месяц", "duration_days": 30, "price_rub": 199},
    {"slug": "month_3", "title": "eBoost на 3 месяца", "duration_days": 90, "price_rub": 499},
    {"slug": "month_12", "title": "eBoost на 12 месяцев", "duration_days": 365, "price_rub": 1490},
]


async def list_active_plans(session: AsyncSession) -> list[Plan]:
    result = await session.execute(select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.price_rub))
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
            plan.is_active = True
