"""BE-019: background pre-warm of artist_cache from a freshly imported event."""

from __future__ import annotations

import asyncio
import time
import uuid

import structlog
from sqlalchemy import distinct, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models.artist import Artist, SetArtist
from app.db.models.artist_cache import ArtistCache
from app.db.models.set_ import Set
from app.db.session import get_session_maker
from app.services.artist_normalize import normalize
from app.services.artist_service import ArtistUnavailableError, _is_fresh, get_artist_detail

_logger = structlog.get_logger()

_CONCURRENCY = 5
_TIMEOUT_PER_ARTIST = 30.0


async def _prewarm_one(
    session_maker: object,
    artist_name: str,
    settings: Settings,
) -> bool:
    """Fetch a single artist in its own session. Returns True on success."""
    from sqlalchemy.ext.asyncio import async_sessionmaker  # noqa: PLC0415

    sm: async_sessionmaker[AsyncSession] = session_maker  # type: ignore[assignment]
    from app.services.artist_providers.lastfm import LastFmProvider  # noqa: PLC0415
    from app.services.artist_providers.spotify import SpotifyProvider  # noqa: PLC0415

    spotify = SpotifyProvider(
        settings.spotify_client_id, settings.spotify_client_secret.get_secret_value()
    )
    lastfm = LastFmProvider(settings.lastfm_api_key.get_secret_value())
    try:
        async with sm() as db:
            # Skip already-fresh rows
            name_normalized = normalize(artist_name)
            row_result = await db.execute(
                select(ArtistCache).where(ArtistCache.name_normalized == name_normalized)
            )
            row = row_result.scalar_one_or_none()
            if row is not None and _is_fresh(row, settings.artist_cache_ttl_seconds):
                return True
            await get_artist_detail(db, artist_name, spotify, lastfm, settings)
            await db.commit()
            return True
    except (ArtistUnavailableError, Exception):
        _logger.debug("prewarm.artist_failed", artist_name=artist_name)
        return False
    finally:
        await spotify.aclose()
        await lastfm.aclose()


async def prewarm_artists_from_event(event_id: uuid.UUID) -> None:
    """Pre-warm artist_cache for all artists in an event. Fire-and-forget."""
    t0 = time.monotonic()
    settings = Settings()
    session_maker = get_session_maker()

    async with session_maker() as db:
        result = await db.execute(
            select(distinct(Artist.name))
            .join(SetArtist, SetArtist.artist_id == Artist.artist_id)
            .join(Set, Set.set_id == SetArtist.set_id)
            .where(Set.event_id == event_id)
        )
        names = [row[0] for row in result.all()]

    total = len(names)
    _logger.info("artist.prewarm_started", event_id=str(event_id), total=total)

    semaphore = asyncio.Semaphore(_CONCURRENCY)

    async def _bounded(name: str) -> bool:
        async with semaphore:
            try:
                return await asyncio.wait_for(
                    _prewarm_one(session_maker, name, settings),
                    timeout=_TIMEOUT_PER_ARTIST,
                )
            except asyncio.TimeoutError:
                _logger.warning("prewarm.artist_timeout", artist_name=name)
                return False

    results = await asyncio.gather(*[_bounded(n) for n in names], return_exceptions=True)

    succeeded = sum(1 for r in results if r is True)
    failed = total - succeeded
    duration_ms = int((time.monotonic() - t0) * 1000)

    _logger.info(
        "artist.prewarm_complete",
        event_id=str(event_id),
        total=total,
        succeeded=succeeded,
        failed=failed,
        duration_ms=duration_ms,
    )
