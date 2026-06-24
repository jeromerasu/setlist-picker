"""BE-019: GET /api/artists/{artist_name} — cache-first artist detail.
SETLIST-ARTIST-DETAIL: GET /api/artists/{artist_name}/spotify — richer Spotify content.
"""

from __future__ import annotations

import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.config import Settings
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.artists import ArtistDetailResponse, SpotifyArtistDetail
from app.services.artist_providers.lastfm import LastFmProvider
from app.services.artist_providers.spotify import SpotifyProvider
from app.services.artist_service import ArtistUnavailableError, get_artist_detail
from app.services.spotify_service import get_spotify_detail

router = APIRouter(prefix="/api", tags=["artists"])

_settings = Settings()
_spotify = SpotifyProvider(
    _settings.spotify_client_id,
    _settings.spotify_client_secret.get_secret_value(),
)
_lastfm = LastFmProvider(_settings.lastfm_api_key.get_secret_value())


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
