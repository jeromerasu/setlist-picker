"""BE-019: GET /api/artists/{artist_name} — cache-first artist detail.
SETLIST-ARTIST-DETAIL: GET /api/artists/{artist_name}/spotify — Spotify content.
SETLIST-APPLE-MUSIC-INTEGRATION: GET /api/artists/{artist_name}/apple-music — Apple Music content.
"""

from __future__ import annotations

import urllib.parse
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.config import Settings
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.artists import AppleMusicArtistDetail, ArtistDetailResponse, SpotifyArtistDetail
from app.services.apple_music_service import (
    AppleMusicService,
    get_apple_music_detail,
    is_configured,
)
from app.services.artist_providers.lastfm import LastFmProvider
from app.services.artist_providers.spotify import SpotifyProvider
from app.services.artist_service import ArtistUnavailableError, get_artist_detail
from app.services.spotify_service import get_spotify_detail

router = APIRouter(prefix="/api", tags=["artists"])
_logger = structlog.get_logger()

_settings = Settings()
_spotify = SpotifyProvider(
    _settings.spotify_client_id,
    _settings.spotify_client_secret.get_secret_value(),
)
_lastfm = LastFmProvider(_settings.lastfm_api_key.get_secret_value())

# Apple Music service — instantiated only when credentials are present.
_apple_music: AppleMusicService | None = None
if is_configured(
    _settings.apple_music_team_id,
    _settings.apple_music_key_id,
    _settings.apple_music_private_key_base64.get_secret_value(),
):
    _apple_music = AppleMusicService(
        team_id=_settings.apple_music_team_id,
        key_id=_settings.apple_music_key_id,
        private_key_b64=_settings.apple_music_private_key_base64.get_secret_value(),
    )
else:
    _logger.warning(
        "apple_music.credentials_missing",
        detail="APPLE_MUSIC_TEAM_ID / APPLE_MUSIC_KEY_ID / APPLE_MUSIC_PRIVATE_KEY_BASE64 not set; "
               "/apple-music endpoint will return 503",
    )


@router.get("/artists/{artist_name}", response_model=ArtistDetailResponse)
async def get_artist_endpoint(
    artist_name: str,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
) -> ArtistDetailResponse:
    raw_name = urllib.parse.unquote(artist_name)
    try:
        return await get_artist_detail(db, raw_name, _spotify, _lastfm, _settings)
    except ArtistUnavailableError:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "artist_unavailable"},
        )


@router.get("/artists/{artist_name}/spotify", response_model=SpotifyArtistDetail)
async def get_artist_spotify_endpoint(
    artist_name: str,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
    refresh: bool = False,
) -> SpotifyArtistDetail:
    """Return artist photo, genres, and up to 5 top tracks from Spotify.

    Returns 503 if Spotify is unavailable and no cached data exists.
    Returns cached data even if Spotify credentials are not yet configured.
    Pass ?refresh=true to bypass cache and re-run the full Spotify lookup.
    """
    raw_name = urllib.parse.unquote(artist_name)
    try:
        return await get_spotify_detail(
            db,
            raw_name,
            _spotify,
            cache_ttl_seconds=_settings.artist_cache_ttl_seconds,
            force_refresh=refresh,
        )
    except ArtistUnavailableError:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "artist_unavailable"},
        )


@router.get("/artists/{artist_name}/apple-music", response_model=AppleMusicArtistDetail)
async def get_artist_apple_music_endpoint(
    artist_name: str,
    caller: Annotated[User, Depends(current_user)],
    db: AsyncSession = Depends(get_db),
    refresh: bool = False,
) -> AppleMusicArtistDetail:
    """Return artist photo, genres, and up to 5 top tracks from Apple Music.

    Returns 503 if Apple Music credentials are not configured or the artist
    cannot be found and no cached data exists.
    Pass ?refresh=true to bypass cache and force a fresh Apple Music lookup.
    """
    if _apple_music is None:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "apple_music_not_configured"},
        )
    raw_name = urllib.parse.unquote(artist_name)
    try:
        return await get_apple_music_detail(
            db,
            raw_name,
            _apple_music,
            cache_ttl_seconds=_settings.artist_cache_ttl_seconds,
            force_refresh=refresh,
        )
    except ArtistUnavailableError:
        raise HTTPException(
            status_code=503,
            detail={"error_code": "artist_unavailable"},
        )
