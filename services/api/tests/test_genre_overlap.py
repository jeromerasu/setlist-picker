"""BE-019: GenreOverlapProvider unit tests."""

from __future__ import annotations

import pytest
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist_cache import ArtistCache
from app.services.artist_providers.genre_overlap import GenreOverlapProvider


async def _seed_cache(
    db: AsyncSession,
    name_normalized: str,
    genres: list[str],
) -> None:
    stmt = (
        pg_insert(ArtistCache)
        .values(name_normalized=name_normalized, display_name=name_normalized, genres=genres)
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(genres=genres),
        )
    )
    await db.execute(stmt)
    await db.flush()


async def test_jaccard_over_cached_genres(db_session: AsyncSession) -> None:
    """Seed 3 artists with genres; query artist with overlapping genres returns ranked list."""
    await _seed_cache(db_session, "goose", ["jam band", "indie rock", "psychedelic rock"])
    await _seed_cache(db_session, "phish", ["jam band", "progressive rock", "psychedelic rock"])
    await _seed_cache(db_session, "taylor swift", ["pop", "country pop"])

    provider = GenreOverlapProvider(db_session)
    # "eggy" has genres overlapping goose and phish
    result = await provider.get_similar(
        "eggy", genres=["jam band", "indie rock", "psychedelic rock"]
    )

    names = [s.name for s in result]
    # goose is identical → jaccard=1.0; phish has 2/4 → jaccard=0.5; taylor swift has 0
    assert "goose" in names
    assert "phish" in names
    assert "taylor swift" not in names
    # goose should rank first
    assert names[0] == "goose"
    # goose similarity should be 1.0 (identical genre sets)
    assert result[0].similarity == pytest.approx(1.0)
