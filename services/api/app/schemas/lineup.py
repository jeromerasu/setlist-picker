from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class _Model(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=False)


class LineupSourceArtist(_Model):
    id: str
    name: str
    image: str | None = None
    spotify: str | None = None
    instagram: str | None = None
    soundcloud: str | None = None
    tiktok: str | None = None
    twitter: str | None = None
    facebook: str | None = None
    youtube: str | None = None
    website: str | None = None


class LineupSourceStage(_Model):
    id: str
    name: str


class LineupSourcePerformance(_Model):
    id: str
    name: str
    artists: list[LineupSourceArtist] = Field(min_length=1)
    stage: LineupSourceStage
    date: date
    day: str
    startTime: str  # noqa: N815  # source format: 'YYYY-MM-DD HH:MM:SS+HH:MM'
    endTime: str  # noqa: N815


class LineupImportRequest(_Model):
    event_name: str
    start_date: date
    end_date: date
    timezone: str
    location: str | None = None
    source_adapter: Literal["event_api_v1", "manual"]
    external_id: str | None = None
    performances: list[LineupSourcePerformance]


class LineupImportResponse(_Model):
    event_id: UUID
    stages_created: int
    stages_updated: int
    sets_created: int
    sets_updated: int
    artists_created: int
    artists_linked: int
    imported_at: datetime
