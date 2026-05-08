from __future__ import annotations

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from eboost.db.base import Base


PLAN_KIND_SUBSCRIPTION = "subscription"
PLAN_KIND_DEVICE_PACK = "device_pack"


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    duration_days: Mapped[int] = mapped_column(Integer, nullable=False)
    price_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    kind: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=PLAN_KIND_SUBSCRIPTION,
        server_default=PLAN_KIND_SUBSCRIPTION,
    )
    bonus_devices: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    @property
    def is_device_pack(self) -> bool:
        return self.kind == PLAN_KIND_DEVICE_PACK
