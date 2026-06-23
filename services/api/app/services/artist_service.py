"""BE-019: cache-first artist detail fetcher."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.db.models.artist_cache import ArtistCache
from app.schemas.artists import (
    ArtistDetailResponse,
    CacheStatus,
    SimilarArtist,
    TopTrack,
)
from app.services.artist_normalize import normalize
from app.services.artist_providers.genre_overlap import GenreOverlapProvider
from app.services.artist_providers.lastfm import LastFmProvider
from app.services.artist_providers.spotify import SpotifyProvider

_logger = structlog.get_logger()


def _is_fresh(row: ArtistCache, ttl_seconds: int) -> bool:
    if row.fetched_at is None:
        return False
    threshold = datetime.now(timezone.utc) - timedelta(seconds=ttl_seconds)
    return row.fetched_at >= threshold


def _in_backoff(row: ArtistCache, max_backoff_hours: int) -> bool:
    if row.fetch_failure_count == 0 or row.last_failure_at is None:
        return False
    backoff_hours = min(2 ** (row.fetch_failure_count - 1), max_backoff_hours)
    window_end = row.last_failure_at + timedelta(hours=backoff_hours)
    return datetime.now(timezone.utc) < window_end


def _row_to_response(row: ArtistCache, status: CacheStatus) -> ArtistDetailResponse:
    similar: list[SimilarArtist] = []
    if row.similar_artists:
        for item in row.similar_artists:
            name = str(item.get("name", ""))
            sim = item.get("similarity")
            sim_float: float | None = float(str(sim)) if sim is not None else None
            similar.append(SimilarArtist(name=name, similarity=sim_float))

    top_track: TopTrack | None = None
    if row.top_track:
        top_track = TopTrack(
            name=str(row.top_track.get("name", "")),
            preview_url=str(row.top_track["preview_url"])
            if row.top_track.get("preview_url")
            else None,
            external_url=str(row.top_track["external_url"])
            if row.top_track.get("external_url")
            else None,
        )

    return ArtistDetailResponse(
        artist_name=row.display_name or row.name_normalized,
        spotify_artist_id=row.spotify_artist_id,
        image_url=row.image_url,
        genres=row.genres or [],
        similar_artists=similar,
        top_track=top_track,
        cache_status=status,
        similarity_source=row.similarity_source,
        fetched_at=row.fetched_at,
    )


async def _load_cache_row(db: AsyncSession, name_normalized: str) -> ArtistCache | None:
    result = await db.execute(
        select(ArtistCache)
        .where(ArtistCache.name_normalized == name_normalized)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def get_artist_detail(
    db: AsyncSession,
    raw_name: str,
    spotify: SpotifyProvider,
    lastfm: LastFmProvider,
    settings: Settings | None = None,
) -> ArtistDetailResponse:
    cfg = settings or Settings()
    name_normalized = normalize(raw_name)
    t0 = time.monotonic()

    row = await _load_cache_row(db, name_normalized)

    if row is not None:
        if _is_fresh(row, cfg.artist_cache_ttl_seconds):
            _logger.debug("artist.cache_hit_fresh", name_normalized=name_normalized)
            return _row_to_response(row, "fresh")

        if row.fetch_failure_count > 0 and _in_backoff(row, cfg.artist_max_backoff_hours):
            _logger.debug(
                "artist.cache_hit_stale",
                name_normalized=name_normalized,
                in_backoff=True,
            )
            return _row_to_response(row, "stale")

        _logger.debug(
            "artist.cache_hit_stale",
            name_normalized=name_normalized,
            in_backoff=False,
        )

    _logger.info("artist.fetch_started", name_normalized=name_normalized)

    try:
        provider_artist = await spotify.search_and_fetch(name_normalized)
    except Exception:
        provider_artist = None

    genres: list[str] = provider_artist.genres if provider_artist else []
    spotify_ok = provider_artist is not None

    genre_overlap = GenreOverlapProvider(db)
    try:
        similar = await lastfm.get_similar(name_normalized, genres)
        lastfm_ok = True
        similarity_source = "lastfm" if similar else None
    except Exception:
        similar = []
        lastfm_ok = False
        similarity_source = None

    if not similar:
        try:
            similar = await genre_overlap.get_similar(name_normalized, genres)
            if similar:
                similarity_source = "genre_overlap"
        except Exception:
            similar = []

    if similarity_source is None and not similar:
        similarity_source = "none"

    duration_ms = int((time.monotonic() - t0) * 1000)

    if not spotify_ok and not lastfm_ok and not similar:
        # Total failure
        failure_count = (row.fetch_failure_count if row else 0) + 1
        now = datetime.now(timezone.utc)
        next_backoff_s = min(2 ** (failure_count - 1), cfg.artist_max_backoff_hours) * 3600
        _logger.warning(
            "artist.fetch_failed",
            name_normalized=name_normalized,
            failure_count=failure_count,
            next_backoff_seconds=next_backoff_s,
        )
        stmt = (
            pg_insert(ArtistCache)
            .values(
                name_normalized=name_normalized,
                display_name=raw_name,
                fetch_failure_count=failure_count,
                last_failure_at=now,
            )
            .on_conflict_do_update(
                index_elements=["name_normalized"],
                set_=dict(
                    fetch_failure_count=failure_count,
                    last_failure_at=now,
                ),
            )
        )
        await db.execute(stmt)
        await db.flush()

        if row is not None:
            _logger.error("artist.unavailable", name_normalized=name_normalized)
            # Return stale cached data rather than 503 when we have something
            row2 = await _load_cache_row(db, name_normalized)
            if row2 and (row2.genres or row2.similar_artists or row2.top_track):
                return _row_to_response(row2, "stale")
        _logger.error("artist.unavailable", name_normalized=name_normalized)
        raise ArtistUnavailableError(name_normalized)

    _logger.info(
        "artist.fetch_complete",
        name_normalized=name_normalized,
        spotify_ok=spotify_ok,
        lastfm_ok=lastfm_ok,
        similarity_source=similarity_source,
        duration_ms=duration_ms,
    )

    now = datetime.now(timezone.utc)
    top_track_dict: dict[str, object] | None = None
    if provider_artist and provider_artist.top_track:
        tt = provider_artist.top_track
        top_track_dict = {
            "name": tt.name,
            "preview_url": tt.preview_url,
            "external_url": tt.external_url,
        }

    similar_dicts: list[dict[str, object]] = [
        {"name": s.name, "similarity": s.similarity} for s in similar
    ]

    stmt2 = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=name_normalized,
            display_name=raw_name,
            spotify_artist_id=provider_artist.spotify_artist_id if provider_artist else None,
            image_url=provider_artist.image_url if provider_artist else None,
            genres=genres or None,
            similar_artists=similar_dicts or None,
            top_track=top_track_dict,
            similarity_source=similarity_source,
            fetched_at=now,
            fetch_failure_count=0,
            last_failure_at=None,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(
                display_name=raw_name,
                spotify_artist_id=pg_insert(ArtistCache).excluded.spotify_artist_id,
                image_url=pg_insert(ArtistCache).excluded.image_url,
                genres=pg_insert(ArtistCache).excluded.genres,
                similar_artists=pg_insert(ArtistCache).excluded.similar_artists,
                top_track=pg_insert(ArtistCache).excluded.top_track,
                similarity_source=pg_insert(ArtistCache).excluded.similarity_source,
                fetched_at=now,
                fetch_failure_count=0,
                last_failure_at=None,
            ),
        )
    )
    await db.execute(stmt2)
    await db.flush()

    refreshed = await _load_cache_row(db, name_normalized)
    if refreshed is None:
        raise ArtistUnavailableError(name_normalized)
    return _row_to_response(refreshed, "fresh")


class ArtistUnavailableError(Exception):
    def __init__(self, name_normalized: str) -> None:
        super().__init__(f"artist unavailable: {name_normalized}")
        self.name_normalized = name_normalized
