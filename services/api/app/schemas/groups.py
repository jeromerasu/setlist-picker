from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class GroupCreate(_Model):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    event_id: UUID

    @field_validator("name", mode="before")
    @classmethod
    def strip_and_validate_name(cls, v: object) -> object:
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                raise ValueError("name_blank")
            return stripped
        return v


class GroupCreateResponse(_Model):
    group_id: UUID
    name: str
    invite_code: str = Field(min_length=8, max_length=8)
    event_id: UUID
    created_by_user_id: UUID
    created_at: datetime
    member_id: UUID


class GroupJoinRequest(_Model):
    invite_code: str = Field(min_length=8, max_length=8)
    display_name_override: str | None = Field(default=None, min_length=1, max_length=80)


class MemberOut(_Model):
    member_id: UUID
    user_id: UUID
    group_id: UUID
    display_name: str
    display_name_override: str | None
    avatar_color: str
    joined_at: datetime


class MyGroupListItem(_Model):
    group_id: UUID
    name: str
    invite_code: str = Field(min_length=8, max_length=8)
    event_id: UUID
    created_by_user_id: UUID
    last_active_at: datetime
    archived_at: datetime | None
    member_id: UUID
    joined_at: datetime


class GroupJoinResponse(_Model):
    group: MyGroupListItem
    member: MemberOut
    is_new_member: bool


class MyGroupListResponse(_Model):
    groups: list[MyGroupListItem]


class EventSummary(_Model):
    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str


class PickSummary(_Model):
    member_id: UUID
    set_id: UUID
    state: str
    state_clock_ms: int = Field(ge=0)


class GroupStateResponse(_Model):
    group_id: UUID
    invite_code: str
    name: str
    event: EventSummary
    members: list[MemberOut]
    picks: list[PickSummary]
    archived_at: datetime | None
    last_active_at: datetime
