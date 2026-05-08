from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from eboost.db.base import Base
from eboost.models.common import TimestampMixin


class NotificationType:
    START_NO_TRIAL_1H = "start_no_trial_1h"
    START_NO_TRIAL_24H = "start_no_trial_24h"
    TRIAL_EXPIRE_24H = "trial_expire_24h"
    TRIAL_EXPIRED = "trial_expired"
    CONNECTED_24H = "connected_24h"
    SUB_EXPIRE_3D = "sub_expire_3d"
    SUB_EXPIRE_1D = "sub_expire_1d"
    SUB_EXPIRED = "sub_expired"


class SubscriptionNotification(TimestampMixin, Base):
    __tablename__ = "subscription_notifications"
    __table_args__ = (UniqueConstraint("user_id", "kind", "subscription_until_key", name="uq_subscription_notice"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    subscription_until_key: Mapped[str] = mapped_column(String(64), nullable=False)


class NotificationLog(Base):
    __tablename__ = "notifications_log"
    __table_args__ = (UniqueConstraint("user_id", "type", name="uq_notifications_log_user_type"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
