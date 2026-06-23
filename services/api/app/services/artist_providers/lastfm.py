"""Last.fm provider — similar artists via artist.getsimilar."""

from __future__ import annotations

import httpx
import structlog

from app.schemas.artists import SimilarArtist

_logger = structlog.get_logger()

_API_BASE = "https://ws.audioscrobbler.com/2.0/"
_CONNECT_TIMEOUT = 5.0
_READ_TIMEOUT = 10.0


class LastFmProvider:
    """Similar artists from Last.fm; fails-safe to [] on 5xx."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._http = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=_CONNECT_TIMEOUT, read=_READ_TIMEOUT, write=5.0, pool=5.0)
        )

    async def get_similar(
        self, name_normalized: str, genres: list[str] | None = None
    ) -> list[SimilarArtist]:
        try:
            r = await self._http.get(
                _API_BASE,
                params={
                    "method": "artist.getsimilar",
                    "artist": name_normalized,
                    "api_key": self._api_key,
                    "format": "json",
                    "limit": "10",
                },
            )
            if r.status_code >= 500:
                _logger.debug("lastfm.5xx", status=r.status_code)
                return []
            r.raise_for_status()
            data = r.json()
            similar: list[dict[str, object]] = data.get("similarartists", {}).get("artist") or []
            return [
                SimilarArtist(
                    name=str(a["name"]),
                    similarity=float(str(a.get("match", 0) or 0)),
                )
                for a in similar
                if "name" in a
            ]
        except (httpx.HTTPStatusError, httpx.TransportError, ValueError):
            _logger.debug("lastfm.request_failed", name_normalized=name_normalized)
            return []

    async def aclose(self) -> None:
        await self._http.aclose()
