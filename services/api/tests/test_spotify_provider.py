"""BE-019: SpotifyProvider unit tests (httpx mocked)."""

from __future__ import annotations

import time
from typing import Any

import httpx
import pytest

from app.services.artist_providers.protocol import RateLimited
from app.services.artist_providers.spotify import SpotifyProvider

_TOKEN_RESP = {
    "access_token": "tok-abc123",
    "token_type": "Bearer",
    "expires_in": 3600,
}

_SEARCH_RESP = {
    "artists": {
        "items": [
            {
                "id": "spotify-id-123",
                "name": "Eggy",
                "genres": ["jam band", "indie rock"],
                "images": [{"url": "https://example.com/eggy.jpg", "height": 640, "width": 640}],
            }
        ]
    }
}

# search?type=track response (replaces deprecated /top-tracks endpoint)
_TRACK_SEARCH_RESP = {
    "tracks": {
        "items": [
            {
                "id": "track-id-1",
                "name": "Movin' On",
                "preview_url": "https://p.scdn.co/preview/123",
                "external_urls": {"spotify": "https://open.spotify.com/track/123"},
                "duration_ms": 237_000,
                "popularity": 72,
                "artists": [{"id": "spotify-id-123", "name": "Eggy"}],
            }
        ]
    }
}


def _make_response(status: int, data: dict[str, Any]) -> httpx.Response:
    return httpx.Response(status_code=status, json=data)


@pytest.fixture
def spotify() -> SpotifyProvider:
    return SpotifyProvider(client_id="cid", client_secret="csecret")


async def test_spotify_search_and_fetch_happy_path(spotify: SpotifyProvider) -> None:
    """Full happy path: token → artist search → track search (3 requests, token cached)."""
    call_responses = [
        _make_response(200, _TOKEN_RESP),        # POST /api/token
        _make_response(200, _SEARCH_RESP),       # GET /search?type=artist
        _make_response(200, _TRACK_SEARCH_RESP), # GET /search?type=track
    ]
    call_iter = iter(call_responses)

    async def _fake_request(request: httpx.Request) -> httpx.Response:
        return next(call_iter)

    spotify._http = httpx.AsyncClient(transport=httpx.MockTransport(_fake_request))

    result = await spotify.search_and_fetch("eggy")
    assert result is not None
    assert result.spotify_artist_id == "spotify-id-123"
    assert "jam band" in result.genres
    assert result.image_url == "https://example.com/eggy.jpg"
    assert result.top_track is not None
    assert result.top_track.name == "Movin' On"
    assert result.top_track.preview_url == "https://p.scdn.co/preview/123"
    assert result.top_track.duration_ms == 237_000


async def test_spotify_client_credentials_cached(spotify: SpotifyProvider) -> None:
    """Token fetched once; second search within TTL doesn't re-fetch."""
    token_call_count = 0

    async def _fake_request(request: httpx.Request) -> httpx.Response:
        nonlocal token_call_count
        url = str(request.url)
        if "api/token" in url:
            token_call_count += 1
            return _make_response(200, _TOKEN_RESP)
        if "type=artist" in url:
            return _make_response(200, _SEARCH_RESP)
        if "type=track" in url:
            return _make_response(200, _TRACK_SEARCH_RESP)
        # fallback (should not be reached)
        return _make_response(200, {})

    spotify._http = httpx.AsyncClient(transport=httpx.MockTransport(_fake_request))

    await spotify.search_and_fetch("eggy")
    await spotify.search_and_fetch("eggy")

    assert token_call_count == 1


async def test_spotify_token_refresh_on_expiry(spotify: SpotifyProvider) -> None:
    """Expired token triggers a fresh token request on next call."""
    token_call_count = 0

    async def _fake_request(request: httpx.Request) -> httpx.Response:
        nonlocal token_call_count
        url = str(request.url)
        if "api/token" in url:
            token_call_count += 1
            return _make_response(200, _TOKEN_RESP)
        if "type=artist" in url:
            return _make_response(200, _SEARCH_RESP)
        if "type=track" in url:
            return _make_response(200, _TRACK_SEARCH_RESP)
        return _make_response(200, {})

    spotify._http = httpx.AsyncClient(transport=httpx.MockTransport(_fake_request))

    # First call
    await spotify.search_and_fetch("eggy")
    assert token_call_count == 1

    # Manually expire the token
    spotify._token_expires_at = time.monotonic() - 1

    # Second call must re-fetch token
    await spotify.search_and_fetch("eggy")
    assert token_call_count == 2


async def test_spotify_429_raises_retry_after(spotify: SpotifyProvider) -> None:
    """Mock 429 + Retry-After header → RateLimited(retry_after=30)."""

    async def _fake_request(request: httpx.Request) -> httpx.Response:
        if "api/token" in str(request.url):
            return _make_response(200, _TOKEN_RESP)
        return httpx.Response(
            status_code=429,
            headers={"Retry-After": "30"},
            json={},
        )

    spotify._http = httpx.AsyncClient(transport=httpx.MockTransport(_fake_request))

    with pytest.raises(RateLimited) as exc_info:
        await spotify.search_and_fetch("eggy")

    assert exc_info.value.retry_after == 30
