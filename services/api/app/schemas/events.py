from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=False)


class EventListItem(_Model):
    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str


class EventListResponse(_Model):
    events: list[EventListItem]


class ArtistRef(_Model):
    artist_id: UUID
    name: str
    position: int
    spotify_artist_id: str | None


class SetDetail(_Model):
    set_id: UUID
    display_name: str
    day_label: str
    starts_at: datetime
    ends_at: datetime
    artists: list[ArtistRef]


class StageDetail(_Model):
    stage_id: UUID
    name: str
    display_order: int
    sets: list[SetDetail]


class EventLineupResponse(_Model):
    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str
    stages: list[StageDetail]
    sets: list[SetDetail] = Field(default_factory=list)
