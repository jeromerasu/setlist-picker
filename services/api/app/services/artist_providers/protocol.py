"""Shared types and protocols for artist data providers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.schemas.artists import SimilarArtist, TopTrack


class RateLimited(Exception):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"rate limited; retry after {retry_after}s")
        self.retry_after = retry_after


@dataclass
class ProviderArtist:
    name: str
    spotify_artist_id: str | None = None
    image_url: str | None = None
    genres: list[str] = field(default_factory=list)
    top_track: TopTrack | None = None


@runtime_checkable
class MusicDataProvider(Protocol):
    async def search_and_fetch(self, name_normalized: str) -> ProviderArtist | None: ...


@runtime_checkable
class SimilarArtistsProvider(Protocol):
    async def get_similar(
        self, name_normalized: str, genres: list[str] | None
    ) -> list[SimilarArtist]: ...
