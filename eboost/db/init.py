from __future__ import annotations

from eboost.core.config import get_settings
from eboost.db.base import Base
from eboost.db.session import engine
from eboost import models  # noqa: F401


async def create_sqlite_schema_for_local_dev() -> None:
    settings = get_settings()
    if not settings.database_url.startswith("sqlite"):
        return
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
