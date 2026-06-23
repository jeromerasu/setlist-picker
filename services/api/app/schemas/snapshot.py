from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class SnapshotMember(_Model):
    user_id: UUID
    member_id: UUID
    display_name: str
    avatar_color: str


class SnapshotSet(_Model):
    set_id: UUID
    display_name: str
    artist_names: list[str]
    day_label: str
    starts_at: datetime
    ends_at: datetime
    pickers: list[SnapshotMember]


class SnapshotStage(_Model):
    stage_id: UUID
    name: str
    display_order: int
    sets: list[SnapshotSet]


class GroupSnapshotResponse(_Model):
    group_id: UUID
    invite_code: str
    group_name: str
    event_id: UUID
    event_name: str
    timezone: str
    snapshot_at: datetime
    window_minutes: int = Field(ge=5, le=360)
    members_total: int
    stages: list[SnapshotStage]
