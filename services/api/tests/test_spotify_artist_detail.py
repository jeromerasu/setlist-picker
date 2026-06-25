"""SETLIST-ARTIST-DETAIL: GET /api/artists/{name}/spotify endpoint tests."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist_cache import ArtistCache
from app.schemas.artists import SpotifyArtistDetail, TopTrack
from tests.conftest import signup_and_get_token

_FIVE_TRACKS = [
    TopTrack(
        name=f"Track {i}",
        preview_url=f"https://p.scdn.co/{i}",
        spotify_url=f"https://open.spotify.com/t/{i}",
        duration_ms=200_000 + i * 1000,
    )
    for i in range(1, 6)
]

_SPOTIFY_DETAIL = SpotifyArtistDetail(
    artist_name="Fisher",
    image_url="https://img.example.com/fisher.jpg",
    genres=["techno", "house"],
    top_tracks=_FIVE_TRACKS,
)


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    token, _ = await signup_and_get_token(client, "spotify_detail_test@example.com")
    return {"Authorization": f"Bearer {token}"}


async def _seed_cache(
    db: AsyncSession,
    name_normalized: str,
    top_tracks: list[dict[str, Any]] | None = None,
    spotify_artist_id: str | None = "spot-fisher",
    image_url: str | None = "https://img.example.com/fisher.jpg",
    genres: list[str] | None = None,
) -> None:
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=name_normalized,
            display_name=name_normalized,
            spotify_artist_id=spotify_artist_id,
            image_url=image_url,
            genres=genres or ["techno", "house"],
            top_tracks=top_tracks,
            fetched_at=datetime.now(timezone.utc),
            fetch_failure_count=0,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(
                spotify_artist_id=spotify_artist_id,
                image_url=image_url,
                genres=genres or ["techno", "house"],
                top_tracks=top_tracks,
                fetched_at=datetime.now(timezone.utc),
                fetch_failure_count=0,
            ),
        )
    )
    await db.execute(stmt)
    await db.flush()


# ── Endpoint availability ─────────────────────────────────────────────────────


async def test_unauthenticated_spotify_endpoint_returns_401(client: AsyncClient) -> None:
    import httpx

    from app.main import app as _app

    transport = httpx.ASGITransport(app=_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as bare_client:
        r = await bare_client.get("/api/artists/fisher/spotify")
    assert r.status_code == 401


async def test_no_cached_data_and_spotify_fails_returns_503(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """No cache + Spotify search fails → 503 artist_unavailable (creds missing or network error)."""
    with patch(
        "app.services.spotify_service.SpotifyProvider.search_and_fetch",
        new_callable=AsyncMock,
        side_effect=Exception("credentials not configured"),
    ):
        r = await client.get("/api/artists/no-cache-artist/spotify", headers=auth_headers)
    assert r.status_code == 503
    assert r.json()["detail"]["error_code"] == "artist_unavailable"


# ── Cache hit ─────────────────────────────────────────────────────────────────


async def test_cache_hit_with_top_tracks_returns_without_spotify_call(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Hot cache with top_tracks → Spotify not called."""
    tracks = [
        {
            "name": f"Track {i}",
            "preview_url": None,
            "spotify_url": f"https://open.spotify.com/t/{i}",
            "duration_ms": 200_000,
        }
        for i in range(5)
    ]
    await _seed_cache(db_session, "fisher", top_tracks=tracks)

    with patch(
        "app.services.spotify_service.SpotifyProvider.get_top_tracks",
        new_callable=AsyncMock,
    ) as mock_tracks:
        r = await client.get("/api/artists/fisher/spotify", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert data["artist_name"] == "fisher"
    assert len(data["top_tracks"]) == 5
    mock_tracks.assert_not_called()


async def test_cache_hit_no_top_tracks_fetches_and_stores(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Cache row with spotify_artist_id but no top_tracks → fetches tracks, caches them."""
    await _seed_cache(db_session, "fisher", top_tracks=None, spotify_artist_id="spot-fisher")

    with patch(
        "app.services.spotify_service.SpotifyProvider.get_top_tracks",
        new_callable=AsyncMock,
        return_value=_FIVE_TRACKS,
    ):
        r = await client.get("/api/artists/fisher/spotify", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert len(data["top_tracks"]) == 5
    assert data["top_tracks"][0]["duration_ms"] is not None


# ── Cache miss ────────────────────────────────────────────────────────────────


async def test_cache_miss_searches_spotify_and_returns_tracks(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """No cache row → calls search_and_fetch then get_top_tracks."""
    from app.services.artist_providers.protocol import ProviderArtist

    provider_artist = ProviderArtist(
        name="Fisher",
        spotify_artist_id="spot-fisher",
        image_url="https://img.example.com/fisher.jpg",
        genres=["techno"],
        top_track=None,
    )

    with (
        patch(
            "app.services.spotify_service.SpotifyProvider.search_and_fetch",
            new_callable=AsyncMock,
            return_value=provider_artist,
        ),
        patch(
            "app.services.spotify_service.SpotifyProvider.get_top_tracks",
            new_callable=AsyncMock,
            return_value=_FIVE_TRACKS,
        ),
    ):
        r = await client.get("/api/artists/fisher/spotify", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert data["image_url"] == "https://img.example.com/fisher.jpg"
    assert "techno" in data["genres"]
    assert len(data["top_tracks"]) == 5


async def test_spotify_search_fails_returns_503(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """No cache + Spotify search fails → 503 artist_unavailable."""
    with patch(
        "app.services.spotify_service.SpotifyProvider.search_and_fetch",
        new_callable=AsyncMock,
        side_effect=Exception("spotify down"),
    ):
        r = await client.get("/api/artists/nobody-cached/spotify", headers=auth_headers)

    assert r.status_code == 503
    assert r.json()["detail"]["error_code"] == "artist_unavailable"


# ── Response shape ────────────────────────────────────────────────────────────


async def test_top_tracks_have_required_fields(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Each top_track has name, preview_url, spotify_url, duration_ms."""
    tracks = [
        {
            "name": "Losing It",
            "preview_url": "https://p.scdn.co/1",
            "spotify_url": "https://open.spotify.com/t/1",
            "duration_ms": 345_000,
        }
    ]
    await _seed_cache(db_session, "fisher", top_tracks=tracks)

    r = await client.get("/api/artists/fisher/spotify", headers=auth_headers)
    assert r.status_code == 200
    t = r.json()["top_tracks"][0]
    assert t["name"] == "Losing It"
    assert t["preview_url"] == "https://p.scdn.co/1"
    assert t["spotify_url"] == "https://open.spotify.com/t/1"
    assert t["duration_ms"] == 345_000


async def test_force_refresh_bypasses_fresh_cache(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """?refresh=true skips the hot cache and re-runs Spotify search."""
    tracks = [
        {
            "name": "Cached Track",
            "preview_url": None,
            "spotify_url": "https://open.spotify.com/t/cached",
            "duration_ms": 180_000,
        }
    ]
    await _seed_cache(db_session, "fisher", top_tracks=tracks, spotify_artist_id="spot-fisher")

    from app.services.artist_providers.protocol import ProviderArtist

    fresh_artist = ProviderArtist(
        name="Fisher",
        spotify_artist_id="spot-fisher",
        image_url="https://img.example.com/fisher-new.jpg",
        genres=["techno", "house", "dj"],
        top_track=None,
    )

    with (
        patch(
            "app.services.spotify_service.SpotifyProvider.search_and_fetch",
            new_callable=AsyncMock,
            return_value=fresh_artist,
        ) as mock_search,
        patch(
            "app.services.spotify_service.SpotifyProvider.get_top_tracks",
            new_callable=AsyncMock,
            return_value=_FIVE_TRACKS,
        ),
    ):
        r = await client.get("/api/artists/fisher/spotify?refresh=true", headers=auth_headers)

    assert r.status_code == 200
    mock_search.assert_called_once()
    data = r.json()
    assert len(data["top_tracks"]) == 5


async def test_force_refresh_false_serves_hot_cache(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Without ?refresh=true, a hot cache with top_tracks is served without calling Spotify."""
    tracks = [
        {
            "name": "Cached Track",
            "preview_url": None,
            "spotify_url": "https://open.spotify.com/t/cached",
            "duration_ms": 180_000,
        }
    ]
    await _seed_cache(db_session, "fisher", top_tracks=tracks, spotify_artist_id="spot-fisher")

    with patch(
        "app.services.spotify_service.SpotifyProvider.search_and_fetch",
        new_callable=AsyncMock,
    ) as mock_search:
        r = await client.get("/api/artists/fisher/spotify", headers=auth_headers)

    assert r.status_code == 200
    mock_search.assert_not_called()


async def test_genres_and_image_present_in_response(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    tracks: list[dict[str, object]] = []
    await _seed_cache(
        db_session,
        "fisher",
        top_tracks=tracks,
        genres=["techno", "house"],
        image_url="https://img.example.com/fisher.jpg",
    )

    with patch(
        "app.services.spotify_service.SpotifyProvider.get_top_tracks",
        new_callable=AsyncMock,
        return_value=[],
    ):
        r = await client.get("/api/artists/fisher/spotify", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert data["image_url"] == "https://img.example.com/fisher.jpg"
    assert "techno" in data["genres"]
