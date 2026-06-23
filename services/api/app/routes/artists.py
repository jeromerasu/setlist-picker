"""BE-019: GET /api/artists/{artist_name} — cache-first artist detail."""

from __future__ import annotations

import urllib.parse
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import current_user
from app.config import Settings
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.artists import ArtistDetailResponse
from app.services.artist_providers.lastfm import LastFmProvider
from app.services.artist_providers.spotify import SpotifyProvider
from app.services.artist_service import ArtistUnavailableError, get_artist_detail

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
