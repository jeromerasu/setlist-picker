"""GET /api/artists/{name}/spotify — cache-first Spotify artist detail."""

from __future__ import annotations

import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist_cache import ArtistCache
from app.schemas.artists import SpotifyArtistDetail, TopTrack
from app.services.artist_normalize import normalize
from app.services.artist_providers.spotify import SpotifyProvider
from app.services.artist_service import ArtistUnavailableError, _is_fresh

_logger = structlog.get_logger()


async def get_spotify_detail(
    db: AsyncSession,
    raw_name: str,
    spotify: SpotifyProvider,
    cache_ttl_seconds: int = 604800,
) -> SpotifyArtistDetail:
    """Return Spotify image + genres + up-to-5 top tracks. Cache-first; 503 on total failure."""
    name_normalized = normalize(raw_name)

    row = await _load_row(db, name_normalized)

    # Fresh cache with top_tracks already populated → serve immediately
    if row is not None and _is_fresh(row, cache_ttl_seconds) and row.top_tracks:
        _logger.debug("spotify_detail.cache_hit", name_normalized=name_normalized)
        return _row_to_response(raw_name, row)

    # If spotify_artist_id is known (from previous full fetch), use it directly
    spotify_artist_id: str | None = row.spotify_artist_id if row else None

    if spotify_artist_id is None:
        # Need to search Spotify for the artist
        try:
            provider_artist = await spotify.search_and_fetch(name_normalized)
        except Exception:
            _logger.warning("spotify_detail.search_failed", name_normalized=name_normalized)
            provider_artist = None

        if provider_artist is None:
            # No Spotify data at all — return cached image/genres if available, else 503
            if row is not None and (row.image_url or row.genres):
                return _row_to_response(raw_name, row)
            raise ArtistUnavailableError(name_normalized)

        spotify_artist_id = provider_artist.spotify_artist_id

        # Persist image + genres if not already cached
        await _upsert_base(
            db, name_normalized, raw_name, provider_artist.image_url, provider_artist.genres
        )
        row = await _load_row(db, name_normalized)

    # Fetch top 5 tracks using known spotify_artist_id
    top_tracks: list[TopTrack] = []
    if spotify_artist_id:
        try:
            top_tracks = await spotify.get_top_tracks(spotify_artist_id, limit=5)
        except Exception:
            _logger.warning(
                "spotify_detail.top_tracks_failed",
                name_normalized=name_normalized,
                spotify_artist_id=spotify_artist_id,
            )

    # Persist top_tracks into cache
    top_tracks_dicts: list[dict[str, object]] = [
        {
            "name": t.name,
            "preview_url": t.preview_url,
            "spotify_url": t.spotify_url,
            "duration_ms": t.duration_ms,
        }
        for t in top_tracks
    ]
    await _upsert_top_tracks(db, name_normalized, top_tracks_dicts)

    image_url = row.image_url if row else None
    genres = row.genres or [] if row else []
    return SpotifyArtistDetail(
        artist_name=raw_name,
        image_url=image_url,
        genres=genres,
        top_tracks=top_tracks,
    )


def _row_to_response(raw_name: str, row: ArtistCache) -> SpotifyArtistDetail:
    top_tracks: list[TopTrack] = []
    for item in row.top_tracks or []:
        top_tracks.append(TopTrack(
            name=str(item.get("name", "")),
            preview_url=str(item["preview_url"]) if item.get("preview_url") else None,
            spotify_url=str(item["spotify_url"]) if item.get("spotify_url") else None,
            external_url=str(item["spotify_url"]) if item.get("spotify_url") else None,
            duration_ms=(
                int(str(item["duration_ms"])) if item.get("duration_ms") is not None else None
            ),
        ))
    return SpotifyArtistDetail(
        artist_name=raw_name,
        image_url=row.image_url,
        genres=row.genres or [],
        top_tracks=top_tracks,
    )


async def _load_row(db: AsyncSession, name_normalized: str) -> ArtistCache | None:
    result = await db.execute(
        select(ArtistCache)
        .where(ArtistCache.name_normalized == name_normalized)
        .execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def _upsert_base(
    db: AsyncSession,
    name_normalized: str,
    display_name: str,
    image_url: str | None,
    genres: list[str],
) -> None:
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=name_normalized,
            display_name=display_name,
            image_url=image_url,
            genres=genres or None,
            fetch_failure_count=0,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(
                image_url=pg_insert(ArtistCache).excluded.image_url,
                genres=pg_insert(ArtistCache).excluded.genres,
            ),
        )
    )
    await db.execute(stmt)
    await db.flush()


async def _upsert_top_tracks(
    db: AsyncSession,
    name_normalized: str,
    top_tracks: list[dict[str, object]],
) -> None:
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=name_normalized,
            display_name=name_normalized,
            top_tracks=top_tracks or None,
            fetch_failure_count=0,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(top_tracks=pg_insert(ArtistCache).excluded.top_tracks),
        )
    )
    await db.execute(stmt)
    await db.flush()
