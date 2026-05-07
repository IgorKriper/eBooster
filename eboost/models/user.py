from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from eboost.db.base import Base
from eboost.models.common import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(255))
    first_name: Mapped[str | None] = mapped_column(String(255))
    referral_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    referrer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), index=True)
    trial_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    subscription_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    vpn_user_id: Mapped[str | None] = mapped_column(String(255))
    vpn_subscription_url: Mapped[str | None] = mapped_column(Text)
    bonus_days: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    referrer: Mapped["User | None"] = relationship(remote_side="User.id", foreign_keys=[referrer_id])
