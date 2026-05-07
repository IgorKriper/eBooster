from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from eboost.services.documents import seed_documents
from eboost.services.plans import seed_plans
from eboost.services.promo_codes import seed_promo_codes


async def seed_defaults(session: AsyncSession) -> None:
    await seed_plans(session)
    await seed_documents(session)
    await seed_promo_codes(session)
