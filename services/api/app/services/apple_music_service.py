"""SETLIST-APPLE-MUSIC-INTEGRATION: Apple Music artist detail — JWT signing + cache-first lookup."""

from __future__ import annotations

import base64
import re
import time

import httpx
import structlog
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist_cache import ArtistCache
from app.schemas.artists import AppleMusicArtistDetail, AppleMusicTrack
from app.services.artist_normalize import normalize
from app.services.artist_service import ArtistUnavailableError, _is_fresh

_logger = structlog.get_logger()

_API_BASE = "https://api.music.apple.com/v1/catalog/us"
_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 10.0
# Token valid for 180 days; refresh when < 24 h remain.
_TOKEN_LIFETIME_SECONDS = 180 * 24 * 3600
_REFRESH_WINDOW_SECONDS = 24 * 3600
_ARTWORK_SIZE = "600x600"


def _format_artwork_url(template: str) -> str:
    """Replace Apple's {w}x{h} placeholder with the desired resolution."""
    return re.sub(r"\{w\}x\{h\}", _ARTWORK_SIZE, template)


class AppleMusicService:
    """Apple Music developer-JWT auth + catalog search/fetch.

    Instantiate once at module level. JWT is cached in memory and refreshed
    automatically when within 24 h of expiry.
    """

    def __init__(self, team_id: str, key_id: str, private_key_b64: str) -> None:
        self._team_id = team_id
        self._key_id = key_id
        self._private_key_pem: str = base64.b64decode(private_key_b64).decode("utf-8")
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=5.0, pool=5.0
            )
        )
        self._jwt: str | None = None
        self._jwt_expires_at: float = 0.0

    # ── JWT management ────────────────────────────────────────────────────────

    def _build_jwt(self) -> str:
        from jose import (
            jwt as jose_jwt,  # local import — jose is in deps (python-jose[cryptography])
        )

        now = int(time.time())
        exp = now + _TOKEN_LIFETIME_SECONDS
        payload = {"iss": self._team_id, "iat": now, "exp": exp}
        token: str = jose_jwt.encode(
            payload,
            self._private_key_pem,
            algorithm="ES256",
            headers={"kid": self._key_id, "alg": "ES256"},
        )
        self._jwt = token
        # Store expiry as a wall-clock Unix timestamp for simplicity
        self._jwt_expires_at = float(exp)
        return token

    def _get_jwt(self) -> str:
        now = time.time()
        if self._jwt is None or (self._jwt_expires_at - now) < _REFRESH_WINDOW_SECONDS:
            _logger.info("apple_music.jwt_refresh")
            return self._build_jwt()
        return self._jwt

    # ── HTTP helpers ─────────────────────────────────────────────────────────

    async def _get(self, path: str, params: dict[str, str] | None = None) -> httpx.Response:
        token = self._get_jwt()
        r = await self._http.get(
            f"{_API_BASE}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r

    # ── Public API ───────────────────────────────────────────────────────────

    async def search_artist(
        self, name_normalized: str
    ) -> tuple[str, str, str | None, list[str]] | None:
        """Search for an artist by normalized name.

        Returns (artist_id, display_name, artwork_url, genres) or None.
        """
        r = await self._get(
            "/search",
            params={"term": name_normalized, "types": "artists", "limit": "5"},
        )
        data = r.json()
        artists = data.get("results", {}).get("artists", {}).get("data", [])
        if not artists:
            return None

        # Prefer exact normalized-name match; fall back to first result.
        matched = None
        for item in artists:
            if normalize(item.get("attributes", {}).get("name", "")) == name_normalized:
                matched = item
                break
        if matched is None:
            matched = artists[0]

        attrs = matched.get("attributes", {})
        artist_id: str = matched["id"]
        display_name: str = attrs.get("name", name_normalized)
        genres: list[str] = attrs.get("genreNames", [])
        artwork_template: str = attrs.get("artwork", {}).get("url", "")
        artwork_url: str | None = (
            _format_artwork_url(artwork_template) if artwork_template else None
        )

        return artist_id, display_name, artwork_url, genres

    async def get_top_tracks(self, artist_id: str, limit: int = 5) -> list[AppleMusicTrack]:
        """Fetch up to `limit` top songs for an Apple Music artist ID."""
        r = await self._get(f"/artists/{artist_id}", params={"views": "top-songs"})
        data = r.json()
        songs = (
            data.get("data", [{}])[0]
            .get("views", {})
            .get("top-songs", {})
            .get("data", [])
        )
        tracks: list[AppleMusicTrack] = []
        for song in songs[:limit]:
            attrs = song.get("attributes", {})
            previews: list[dict[str, object]] = attrs.get("previews", [])
            preview_url: str | None = str(previews[0]["url"]) if previews else None
            tracks.append(
                AppleMusicTrack(
                    name=str(attrs.get("name", "")),
                    duration_ms=(
                        int(attrs["durationInMillis"])
                        if attrs.get("durationInMillis") is not None
                        else None
                    ),
                    apple_music_url=str(attrs["url"]) if attrs.get("url") else None,
                    preview_url=preview_url,
                )
            )
        return tracks

    async def aclose(self) -> None:
        await self._http.aclose()


# ── Credentials check ─────────────────────────────────────────────────────────

def is_configured(team_id: str, key_id: str, private_key_b64: str) -> bool:
    return bool(team_id and key_id and private_key_b64)


# ── Cache-first service function ──────────────────────────────────────────────

async def get_apple_music_detail(
    db: AsyncSession,
    raw_name: str,
    service: AppleMusicService,
    cache_ttl_seconds: int = 604800,
    force_refresh: bool = False,
) -> AppleMusicArtistDetail:
    """Return Apple Music photo + genres + top tracks. Cache-first; 503 on total failure."""
    name_normalized = normalize(raw_name)
    row = await _load_row(db, name_normalized)

    # Fresh cache with apple_music top_tracks → serve immediately
    if (
        not force_refresh
        and row is not None
        and _is_fresh(row, cache_ttl_seconds)
        and row.top_tracks
        and row.apple_music_artist_id is not None
    ):
        _logger.debug("apple_music.cache_hit", name_normalized=name_normalized)
        return _row_to_response(raw_name, row)

    # Determine artist ID — use cached value unless force_refresh
    cached_id = row.apple_music_artist_id if row else None
    apple_music_id: str | None = None if force_refresh else cached_id

    artwork_url: str | None = row.image_url if row else None
    genres: list[str] = (row.genres or []) if row else []

    if apple_music_id is None:
        try:
            result = await service.search_artist(name_normalized)
        except Exception:
            _logger.warning("apple_music.search_failed", name_normalized=name_normalized)
            result = None

        if result is None:
            if row is not None and (row.image_url or row.genres):
                return _row_to_response(raw_name, row)
            raise ArtistUnavailableError(name_normalized)

        apple_music_id, _display, artwork_url, genres = result
        await _upsert_base(db, name_normalized, raw_name, apple_music_id, artwork_url, genres)
        row = await _load_row(db, name_normalized)

    # Fetch top tracks
    top_tracks: list[AppleMusicTrack] = []
    if apple_music_id:
        try:
            top_tracks = await service.get_top_tracks(apple_music_id, limit=5)
        except Exception:
            _logger.warning(
                "apple_music.top_tracks_failed",
                name_normalized=name_normalized,
                apple_music_artist_id=apple_music_id,
            )

    # Persist top tracks
    await _upsert_top_tracks(
        db,
        name_normalized,
        [
            {
                "name": t.name,
                "duration_ms": t.duration_ms,
                "apple_music_url": t.apple_music_url,
                "preview_url": t.preview_url,
            }
            for t in top_tracks
        ],
    )

    return AppleMusicArtistDetail(
        artist_name=raw_name,
        apple_music_artist_id=apple_music_id,
        image_url=artwork_url,
        genres=genres,
        top_tracks=top_tracks,
    )


# ── DB helpers ────────────────────────────────────────────────────────────────

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
    apple_music_id: str,
    image_url: str | None,
    genres: list[str],
) -> None:
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=name_normalized,
            display_name=display_name,
            apple_music_artist_id=apple_music_id,
            image_url=image_url,
            genres=genres or None,
            fetch_failure_count=0,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(
                apple_music_artist_id=pg_insert(ArtistCache).excluded.apple_music_artist_id,
                image_url=pg_insert(ArtistCache).excluded.image_url,
                genres=pg_insert(ArtistCache).excluded.genres,
            ),
        )
    )
    await db.execute(stmt)
    await db.flush()


def _row_to_response(raw_name: str, row: ArtistCache) -> AppleMusicArtistDetail:
    top_tracks: list[AppleMusicTrack] = []
    for item in row.top_tracks or []:
        top_tracks.append(
            AppleMusicTrack(
                name=str(item.get("name", "")),
                duration_ms=(
                    int(str(item["duration_ms"]))
                    if item.get("duration_ms") is not None
                    else None
                ),
                apple_music_url=(
                    str(item["apple_music_url"]) if item.get("apple_music_url") else None
                ),
                preview_url=str(item["preview_url"]) if item.get("preview_url") else None,
            )
        )
    return AppleMusicArtistDetail(
        artist_name=raw_name,
        apple_music_artist_id=row.apple_music_artist_id,
        image_url=row.image_url,
        genres=row.genres or [],
        top_tracks=top_tracks,
    )


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
