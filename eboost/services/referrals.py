from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from eboost.core.config import Settings
from eboost.models import Payment, Plan, Referral, User
from eboost.models.payment import PaymentStatus
from eboost.models.plan import PLAN_KIND_SUBSCRIPTION
from eboost.models.referral import ReferralBonusType
from eboost.services import subscriptions
from eboost.services.vpn.base import VpnProvider


async def count_referrals(session: AsyncSession, referrer_id: int) -> int:
    result = await session.execute(select(func.count(User.id)).where(User.referrer_id == referrer_id))
    return int(result.scalar_one())


@dataclass(slots=True)
class ReferrerStats:
    """Aggregated stats for a single referrer.

    All money figures are accumulated from ``Payment.final_amount`` (i.e. the
    amount actually paid after the promo discount), never from the plan's
    catalog price. This is the bug the spec calls out: a 99% promo applied to
    a 200 ₽ plan must contribute 2 ₽, not 200 ₽.
    """

    referrer_id: int
    telegram_id: int
    username: str | None
    first_name: str | None
    invited_total: int
    invited_paying: int
    trial_activations: int
    first_payments: int
    yearly_payments: int
    renewal_payments: int
    revenue_rub: int

    @property
    def display_label(self) -> str:
        if self.username:
            return f"@{self.username} ({self.invited_total} приг., {self.revenue_rub}₽)"
        if self.first_name:
            return f"{self.first_name} (id {self.telegram_id}, {self.invited_total} приг., {self.revenue_rub}₽)"
        return f"id {self.telegram_id} ({self.invited_total} приг., {self.revenue_rub}₽)"


def _yearly_threshold_days() -> int:
    return 300


async def list_referrer_stats(
    session: AsyncSession,
    *,
    limit: int = 50,
) -> list[ReferrerStats]:
    referrer_rows = await session.execute(
        select(User).where(User.referrer_id.is_not(None))
    )
    invited = referrer_rows.scalars().all()

    grouped: dict[int, list[User]] = {}
    for user in invited:
        if user.referrer_id is None:
            continue
        grouped.setdefault(user.referrer_id, []).append(user)

    stats: list[ReferrerStats] = []
    for referrer_id, invited_users in grouped.items():
        referrer = await session.get(User, referrer_id)
        if referrer is None:
            continue

        invited_ids = [u.id for u in invited_users]
        # User has no boolean ``trial_used`` flag — присвоение trial фиксируется
        # установкой ``trial_started_at`` в services.trials.activate_trial.
        trial_count = sum(1 for u in invited_users if u.trial_started_at is not None)

        # Successful payments by all invited users for this referrer.
        payments_q = await session.execute(
            select(Payment, Plan)
            .join(Plan, Plan.id == Payment.plan_id)
            .where(
                Payment.user_id.in_(invited_ids),
                Payment.status == PaymentStatus.SUCCEEDED,
            )
            .order_by(Payment.user_id, Payment.paid_at, Payment.id)
        )
        rows = payments_q.all()

        first_payments = 0
        yearly_payments = 0
        renewal_payments = 0
        revenue = 0
        seen_first: set[int] = set()
        threshold = _yearly_threshold_days()
        for payment, plan in rows:
            revenue += int(payment.final_amount or 0)
            if plan.kind != PLAN_KIND_SUBSCRIPTION:
                continue
            if payment.user_id in seen_first:
                renewal_payments += 1
            else:
                seen_first.add(payment.user_id)
                first_payments += 1
            if (plan.duration_days or 0) >= threshold:
                yearly_payments += 1

        stats.append(
            ReferrerStats(
                referrer_id=referrer.id,
                telegram_id=referrer.telegram_id,
                username=referrer.username,
                first_name=referrer.first_name,
                invited_total=len(invited_users),
                invited_paying=len(seen_first),
                trial_activations=trial_count,
                first_payments=first_payments,
                yearly_payments=yearly_payments,
                renewal_payments=renewal_payments,
                revenue_rub=revenue,
            )
        )

    stats.sort(key=lambda s: (s.revenue_rub, s.invited_total), reverse=True)
    return stats[:limit]


async def get_referrer_stats(
    session: AsyncSession, referrer_id: int
) -> ReferrerStats | None:
    all_stats = await list_referrer_stats(session, limit=10_000)
    for s in all_stats:
        if s.referrer_id == referrer_id:
            return s
    return None


async def award_referral_bonus(
    session: AsyncSession,
    *,
    referred: User,
    bonus_type: str,
    settings: Settings,
    vpn_provider: VpnProvider,
    source_payment_id: int | None = None,
) -> bool:
    if not referred.referrer_id or referred.referrer_id == referred.id:
        return False

    result = await session.execute(
        select(Referral).where(Referral.referred_id == referred.id, Referral.bonus_type == bonus_type)
    )
    if result.scalar_one_or_none():
        return False

    referrer = await session.get(User, referred.referrer_id)
    if not referrer or referrer.id == referred.id:
        return False

    bonus_days = settings.ref_trial_bonus_days if bonus_type == ReferralBonusType.TRIAL else settings.ref_payment_bonus_days
    subscriptions.extend_subscription(referrer, bonus_days)
    referrer.bonus_days += bonus_days
    await subscriptions.sync_vpn_access(referrer, vpn_provider)

    session.add(
        Referral(
            referrer_id=referrer.id,
            referred_id=referred.id,
            bonus_type=bonus_type,
            bonus_days=bonus_days,
            source_payment_id=source_payment_id,
        )
    )
    return True
