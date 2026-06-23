from __future__ import annotations

import uuid
from enum import Enum

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.group_activity import GroupActivity
from app.db.uuid7 import uuid7

_logger = structlog.get_logger()


class ActivityKind(str, Enum):
    group_created = "group_created"
    member_joined = "member_joined"
    member_left = "member_left"
    pick_added = "pick_added"
    pick_removed = "pick_removed"


async def log_activity(
    db: AsyncSession,
    *,
    group_id: uuid.UUID,
    member_id: uuid.UUID | None,
    kind: ActivityKind,
    payload: dict[str, object],
) -> None:
    row = GroupActivity(
        id=uuid7(),
        group_id=group_id,
        member_id=member_id,
        kind=kind.value,
        payload=payload,
    )
    db.add(row)
    await db.flush()
    _logger.debug(
        "activity.logged",
        group_id=str(group_id),
        kind=kind.value,
        member_id=str(member_id) if member_id else None,
    )
