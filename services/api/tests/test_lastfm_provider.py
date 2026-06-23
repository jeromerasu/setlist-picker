"""BE-019: LastFmProvider unit tests (httpx mocked)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from app.services.artist_providers.lastfm import LastFmProvider

_SIMILAR_RESP = {
    "similarartists": {
        "artist": [
            {"name": "Goose", "match": "0.85"},
            {"name": "Phish", "match": "0.72"},
        ]
    }
}


def _make_response(status: int, data: dict[str, Any]) -> httpx.Response:
    return httpx.Response(status_code=status, json=data)


@pytest.fixture
def lastfm() -> LastFmProvider:
    return LastFmProvider(api_key="fake-key")


async def test_lastfm_getsimilar_returns_list(lastfm: LastFmProvider) -> None:
    """Mock response → list of SimilarArtist with similarity_source hint."""

    async def _fake_request(request: httpx.Request) -> httpx.Response:
        return _make_response(200, _SIMILAR_RESP)

    lastfm._http = httpx.AsyncClient(transport=httpx.MockTransport(_fake_request))
    result = await lastfm.get_similar("eggy", genres=None)

    assert len(result) == 2
    names = [s.name for s in result]
    assert "Goose" in names
    assert "Phish" in names
    goose = next(s for s in result if s.name == "Goose")
    assert goose.similarity is not None
    assert abs(goose.similarity - 0.85) < 0.001


async def test_lastfm_5xx_returns_empty(lastfm: LastFmProvider) -> None:
    """503 from Last.fm → empty list; no exception raised."""

    async def _fake_request(request: httpx.Request) -> httpx.Response:
        return _make_response(503, {"message": "Service Unavailable"})

    lastfm._http = httpx.AsyncClient(transport=httpx.MockTransport(_fake_request))
    result = await lastfm.get_similar("eggy", genres=None)

    assert result == []
