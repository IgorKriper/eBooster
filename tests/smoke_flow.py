from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from eboost.core.config import get_settings
from eboost.db.base import Base
from eboost.models.payment import PaymentStatus
from eboost.services import payments, plans, promo_codes, trials, users
from eboost.services.bootstrap import seed_defaults
from eboost.services.payment.factory import get_payment_provider
from eboost.services.vpn.factory import get_vpn_provider


async def run() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    settings = get_settings()
    payment_provider = get_payment_provider(settings)
    vpn_provider = get_vpn_provider(settings)

    async with session_maker() as session:
        await seed_defaults(session)
        referrer = await users.get_or_create_user(
            session,
            telegram_id=100,
            username="ref",
            first_name="Ref",
        )
        referred = await users.get_or_create_user(
            session,
            telegram_id=200,
            username="user",
            first_name="User",
            start_payload=referrer.referral_code,
        )

        activated, message = await trials.activate_trial(
            session,
            user=referred,
            settings=settings,
            vpn_provider=vpn_provider,
        )
        assert activated, message

        plan = (await plans.list_active_plans(session))[-1]
        validation = await promo_codes.validate_promo_code(session, user=referred, code="WELCOME30")
        assert validation.is_valid

        payment = await payments.create_payment(
            session,
            user=referred,
            plan=plan,
            payment_provider=payment_provider,
            promo_code="WELCOME30",
        )
        await payments.complete_payment(
            session,
            payment_id=payment.id,
            status=PaymentStatus.SUCCEEDED,
            settings=settings,
            vpn_provider=vpn_provider,
        )

        assert payment.final_amount == 1393
        assert referred.vpn_subscription_url
        assert referred.subscription_until is not None
        assert referrer.bonus_days == settings.ref_unpaid_bonus_cap_days

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
