from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from eboost.db.base import Base
from eboost.models.common import TimestampMixin


class ServerLoadState(TimestampMixin, Base):
    __tablename__ = "server_load_states"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(16), nullable=False, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=100)
    capacity_mbps: Mapped[int] = mapped_column(Integer, nullable=False, default=900)
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    load_percent: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    rx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    tx_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    last_sample_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    alert_level: Mapped[str | None] = mapped_column(String(16))
    alert_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
