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
    external_url: str | None = None  # kept for backward compat
    spotify_url: str | None = None   # same value as external_url, used by new /spotify endpoint
    duration_ms: int | None = None


class SpotifyArtistDetail(_Model):
    """Response for GET /api/artists/{name}/spotify — richer Spotify content."""
    artist_name: str
    image_url: str | None
    genres: list[str]
    top_tracks: list[TopTrack]


class AppleMusicTrack(_Model):
    name: str
    duration_ms: int | None = None
    apple_music_url: str | None = None
    preview_url: str | None = None


class AppleMusicArtistDetail(_Model):
    """Response for GET /api/artists/{name}/apple-music."""
    artist_name: str
    apple_music_artist_id: str | None
    image_url: str | None
    genres: list[str]
    top_tracks: list[AppleMusicTrack]


class ArtistDetailResponse(_Model):
    artist_name: str
    spotify_artist_id: str | None
    spotify_url: str | None
    image_url: str | None
    genres: list[str]
    similar_artists: list[SimilarArtist]
    top_track: TopTrack | None
    cache_status: CacheStatus
    similarity_source: str | None
    fetched_at: datetime | None
