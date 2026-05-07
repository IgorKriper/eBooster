from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from eboost.core.config import get_settings  # noqa: E402
from eboost.db.base import Base  # noqa: E402
from eboost.models import Payment  # noqa: E402
from eboost.models.payment import PaymentStatus  # noqa: E402
from eboost.services import payments, plans, users  # noqa: E402
from eboost.services.bootstrap import seed_defaults  # noqa: E402
from eboost.services.payment.factory import get_payment_provider  # noqa: E402


async def prepare_payment(database_url: str) -> int:
    engine = create_async_engine(database_url)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    settings = get_settings()
    async with session_maker() as session:
        await seed_defaults(session)
        user = await users.get_or_create_user(
            session,
            telegram_id=300,
            username="backend_test",
            first_name="Backend",
        )
        plan = (await plans.list_active_plans(session))[0]
        payment = await payments.create_payment(
            session,
            user=user,
            plan=plan,
            payment_provider=get_payment_provider(settings),
        )
        await session.commit()
        payment_id = payment.id

    await engine.dispose()
    return payment_id


async def assert_payment_succeeded(database_url: str, payment_id: int) -> None:
    engine = create_async_engine(database_url)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    async with session_maker() as session:
        payment = await session.get(Payment, payment_id)
        assert payment is not None
        assert payment.status == PaymentStatus.SUCCEEDED
    await engine.dispose()


if __name__ == "__main__":
    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./.data/backend_flow.db")
    print(asyncio.run(prepare_payment(db_url)))
