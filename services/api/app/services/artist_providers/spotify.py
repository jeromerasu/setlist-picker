"""Spotify data provider — client-credentials, artist search, top tracks."""

from __future__ import annotations

import time

import httpx
import structlog

from app.schemas.artists import SimilarArtist, TopTrack
from app.services.artist_normalize import normalize as _normalize
from app.services.artist_providers.protocol import ProviderArtist, RateLimited

_logger = structlog.get_logger()

_TOKEN_URL = "https://accounts.spotify.com/api/token"
_API_BASE = "https://api.spotify.com/v1"
_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 10.0


class SpotifyProvider:
    """Spotify artist search + top-tracks via client-credentials flow."""

    def __init__(self, client_id: str, client_secret: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=5.0, pool=5.0)
        )
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    async def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        r = await self._http.post(
            _TOKEN_URL,
            data={"grant_type": "client_credentials"},
            auth=(self._client_id, self._client_secret),
        )
        r.raise_for_status()
        data = r.json()
        self._token = data["access_token"]
        expires_in: int = data["expires_in"]
        self._token_expires_at = time.monotonic() + expires_in - 60  # 60s safety margin
        return self._token

    async def _authed_get(self, url: str, params: dict[str, str] | None = None) -> httpx.Response:
        token = await self._get_token()
        r = await self._http.get(url, params=params, headers={"Authorization": f"Bearer {token}"})
        if r.status_code == 429:
            retry_after = int(r.headers.get("Retry-After", "30"))
            raise RateLimited(retry_after)
        r.raise_for_status()
        return r

    async def search_and_fetch(self, name_normalized: str) -> ProviderArtist | None:
        r = await self._authed_get(
            f"{_API_BASE}/search",
            params={"q": name_normalized, "type": "artist", "limit": "5"},
        )
        artists = r.json().get("artists", {}).get("items", [])
        if not artists:
            return None

        # Pick the artist whose normalized name best matches
        matched = None
        for item in artists:
            if _normalize(item.get("name", "")) == name_normalized:
                matched = item
                break
        if matched is None:
            matched = artists[0]

        artist_id: str = matched["id"]
        genres: list[str] = matched.get("genres") or []
        images: list[dict[str, object]] = matched.get("images") or []
        image_url: str | None = images[0]["url"] if images else None  # type: ignore[assignment]

        top_track = await self._get_top_track(artist_id)

        return ProviderArtist(
            name=matched.get("name", name_normalized),
            spotify_artist_id=artist_id,
            image_url=image_url,
            genres=genres,
            top_track=top_track,
        )

    async def _get_top_track(self, artist_id: str) -> TopTrack | None:
        try:
            r = await self._authed_get(
                f"{_API_BASE}/artists/{artist_id}/top-tracks",
                params={"market": "US"},
            )
            tracks = r.json().get("tracks") or []
            if not tracks:
                return None
            track = tracks[0]
            return TopTrack(
                name=track["name"],
                preview_url=track.get("preview_url"),
                external_url=track.get("external_urls", {}).get("spotify"),
            )
        except Exception:
            _logger.debug("spotify.top_tracks_failed", artist_id=artist_id)
            return None

    async def get_similar(
        self, name_normalized: str, genres: list[str] | None
    ) -> list[SimilarArtist]:
        return []

    async def aclose(self) -> None:
        await self._http.aclose()
