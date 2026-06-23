"""BE-019: artist detail response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class _Model(BaseModel):
    model_config = {"from_attributes": True}


CacheStatus = Literal["fresh", "stale", "miss"]


class SimilarArtist(_Model):
    name: str
    similarity: float | None = None


class TopTrack(_Model):
    name: str
    preview_url: str | None = None
    external_url: str | None = None


class ArtistDetailResponse(_Model):
    artist_name: str
    spotify_artist_id: str | None
    image_url: str | None
    genres: list[str]
    similar_artists: list[SimilarArtist]
    top_track: TopTrack | None
    cache_status: CacheStatus
    similarity_source: str | None
    fetched_at: datetime | None
