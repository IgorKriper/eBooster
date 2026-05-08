from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from eboost.models import AdminLog, SystemLog


def _details(data: dict[str, Any] | None) -> str | None:
    return json.dumps(data, ensure_ascii=False, default=str) if data else None


async def system_log(
    session: AsyncSession,
    *,
    event: str,
    user_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(SystemLog(user_id=user_id, event=event, details=_details(details)))


async def admin_log(
    session: AsyncSession,
    *,
    admin_id: int,
    action: str,
    target_user_id: int | None = None,
    details: dict[str, Any] | None = None,
) -> None:
    session.add(AdminLog(admin_id=admin_id, action=action, target_user_id=target_user_id, details=_details(details)))
