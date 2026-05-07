from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from eboost.db.base import Base
from eboost.models.common import TimestampMixin


class ReferralBonusType:
    TRIAL = "trial"
    PAYMENT = "payment"


class Referral(TimestampMixin, Base):
    __tablename__ = "referrals"
    __table_args__ = (UniqueConstraint("referred_id", "bonus_type", name="uq_referral_referred_bonus_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    referrer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    referred_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    bonus_type: Mapped[str] = mapped_column(String(32), nullable=False)
    bonus_days: Mapped[int] = mapped_column(Integer, nullable=False)
    source_payment_id: Mapped[int | None] = mapped_column(ForeignKey("payments.id", ondelete="SET NULL"))
