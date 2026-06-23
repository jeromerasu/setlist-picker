from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

PickState = Literal["active", "tombstoned"]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class PickCreate(_Model):
    set_id: UUID
    state: PickState
    state_clock_ms: int = Field(ge=0)


class PickResult(_Model):
    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int
    accepted: bool


class PickSyncRequest(_Model):
    toggles: list[PickCreate] = Field(min_length=1, max_length=500)


class PickSyncResponse(_Model):
    results: list[PickResult]


class PickRemoveRequest(_Model):
    state_clock_ms: int = Field(ge=0)
