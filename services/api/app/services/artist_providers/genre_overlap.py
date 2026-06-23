"""Genre-overlap provider — Jaccard similarity over cached artist genres."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist_cache import ArtistCache
from app.schemas.artists import SimilarArtist


class GenreOverlapProvider:
    """Jaccard-based similar-artist fallback using ArtistCache.genres rows."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_similar(
        self, name_normalized: str, genres: list[str] | None
    ) -> list[SimilarArtist]:
        if not genres:
            return []

        target = set(genres)
        result = await self._db.execute(
            select(ArtistCache.name_normalized, ArtistCache.genres).where(
                ArtistCache.genres.is_not(None),
                ArtistCache.name_normalized != name_normalized,
            )
        )
        rows = result.all()

        scored: list[SimilarArtist] = []
        for row in rows:
            candidate_genres: list[str] = row.genres or []
            candidate = set(candidate_genres)
            union = target | candidate
            if not union:
                continue
            jaccard = len(target & candidate) / len(union)
            if jaccard > 0:
                scored.append(SimilarArtist(name=row.name_normalized, similarity=jaccard))

        scored.sort(key=lambda s: s.similarity or 0.0, reverse=True)
        return scored[:10]
