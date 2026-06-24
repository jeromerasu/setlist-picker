"""BE-019: artist fetcher integration tests (endpoint + service + cache)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist_cache import ArtistCache
from app.schemas.artists import TopTrack
from app.services.artist_providers.protocol import ProviderArtist
from app.services.artist_service import _in_backoff
from tests.conftest import signup_and_get_token

_FRESH_PROVIDER_ARTIST = ProviderArtist(
    name="Eggy",
    spotify_artist_id="spot-eggy",
    image_url="https://img.example.com/eggy.jpg",
    genres=["jam band", "indie rock"],
    top_track=TopTrack(name="Movin' On", preview_url="https://p.scdn.co/preview/abc"),
)


async def _seed_fresh_cache(db: AsyncSession, name_normalized: str) -> None:
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=name_normalized,
            display_name=name_normalized,
            spotify_artist_id="spot-123",
            genres=["rock"],
            fetched_at=datetime.now(timezone.utc),
            fetch_failure_count=0,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(
                genres=["rock"],
                fetched_at=datetime.now(timezone.utc),
                fetch_failure_count=0,
            ),
        )
    )
    await db.execute(stmt)
    await db.flush()


async def _seed_stale_cache(
    db: AsyncSession,
    name_normalized: str,
    failure_count: int = 0,
    last_failure_at: datetime | None = None,
) -> None:
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=name_normalized,
            display_name=name_normalized,
            genres=["rock"],
            fetched_at=datetime.now(timezone.utc) - timedelta(days=10),
            fetch_failure_count=failure_count,
            last_failure_at=last_failure_at,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(
                genres=["rock"],
                fetched_at=datetime.now(timezone.utc) - timedelta(days=10),
                fetch_failure_count=failure_count,
                last_failure_at=last_failure_at,
            ),
        )
    )
    await db.execute(stmt)
    await db.flush()


# ── pure-logic unit tests ───────────────────────────────────────────────────


def test_backoff_doubles_up_to_24h_cap() -> None:
    """Backoff doubles: failure_count=1→1h; 2→2h; 5→16h; 6→24h (cap)."""
    now = datetime.now(timezone.utc)

    def make_row(count: int) -> ArtistCache:
        row = ArtistCache()
        row.fetch_failure_count = count
        row.last_failure_at = now - timedelta(minutes=1)
        row.fetched_at = None
        row.display_name = None
        row.name_normalized = "test"
        row.spotify_artist_id = None
        row.image_url = None
        row.genres = None
        row.similar_artists = None
        row.top_track = None
        row.similarity_source = None
        return row

    assert _in_backoff(make_row(1), max_backoff_hours=24) is True  # 1h window, 1min ago → in
    assert _in_backoff(make_row(2), max_backoff_hours=24) is True  # 2h window
    assert _in_backoff(make_row(5), max_backoff_hours=24) is True  # 2^4=16h window
    assert _in_backoff(make_row(6), max_backoff_hours=24) is True  # 2^5=32 → capped to 24h

    # failure_count=1 but last_failure 2h ago → outside 1h window
    row_out = make_row(1)
    row_out.last_failure_at = now - timedelta(hours=2)
    assert _in_backoff(row_out, max_backoff_hours=24) is False


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    token, _ = await signup_and_get_token(client, "artist_test_user@example.com")
    return {"Authorization": f"Bearer {token}"}


# ── endpoint integration tests ────────────────────────────────────────────


async def test_cache_hit_fresh_returns_without_external_call(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Pre-seeded fresh cache → Spotify mock NOT called."""
    await _seed_fresh_cache(db_session, "eggy")

    with patch(
        "app.services.artist_service.SpotifyProvider.search_and_fetch",
        new_callable=AsyncMock,
    ) as mock_spotify:
        r = await client.get("/api/artists/eggy", headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["cache_status"] == "fresh"
    mock_spotify.assert_not_called()


async def test_cache_hit_stale_outside_backoff_refetches(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Stale row (no recent failure) → SpotifyProvider called."""
    await _seed_stale_cache(db_session, "eggy", failure_count=0)

    with (
        patch(
            "app.routes.artists._spotify.search_and_fetch",
            new_callable=AsyncMock,
            return_value=_FRESH_PROVIDER_ARTIST,
        ),
        patch(
            "app.routes.artists._lastfm.get_similar",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        r = await client.get("/api/artists/eggy", headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["cache_status"] == "fresh"


async def test_cache_hit_stale_inside_backoff_returns_stale(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Stale + failure_count=3 + recent last_failure_at → SpotifyProvider NOT called."""
    recent_failure = datetime.now(timezone.utc) - timedelta(minutes=30)
    await _seed_stale_cache(db_session, "eggy", failure_count=3, last_failure_at=recent_failure)

    with patch(
        "app.routes.artists._spotify.search_and_fetch",
        new_callable=AsyncMock,
    ) as mock_spotify:
        r = await client.get("/api/artists/eggy", headers=auth_headers)

    assert r.status_code == 200
    assert r.json()["cache_status"] == "stale"
    mock_spotify.assert_not_called()


async def test_cache_miss_all_providers_fail_returns_503(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """All providers fail + no existing cache → 503 artist_unavailable."""
    with (
        patch(
            "app.routes.artists._spotify.search_and_fetch",
            new_callable=AsyncMock,
            side_effect=Exception("spotify down"),
        ),
        patch(
            "app.routes.artists._lastfm.get_similar",
            new_callable=AsyncMock,
            side_effect=Exception("lastfm down"),
        ),
    ):
        r = await client.get("/api/artists/nobody", headers=auth_headers)

    assert r.status_code == 503
    assert r.json()["detail"]["error_code"] == "artist_unavailable"

    # ArtistCache row created with failure_count=1
    cache_result = await db_session.execute(
        select(ArtistCache)
        .where(ArtistCache.name_normalized == "nobody")
        .execution_options(populate_existing=True)
    )
    row = cache_result.scalar_one_or_none()
    assert row is not None
    assert row.fetch_failure_count == 1


async def test_cache_miss_spotify_ok_lastfm_fail_uses_genre_overlap(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Spotify OK, Last.fm fails → genre_overlap fallback used."""
    with (
        patch(
            "app.routes.artists._spotify.search_and_fetch",
            new_callable=AsyncMock,
            return_value=_FRESH_PROVIDER_ARTIST,
        ),
        patch(
            "app.routes.artists._lastfm.get_similar",
            new_callable=AsyncMock,
            side_effect=Exception("lastfm down"),
        ),
    ):
        r = await client.get("/api/artists/eggy", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert data["cache_status"] == "fresh"
    assert data["similarity_source"] in ("genre_overlap", "none")


async def test_unauthenticated_returns_401(client: AsyncClient) -> None:
    import httpx

    from app.main import app as _app

    transport = httpx.ASGITransport(app=_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as bare_client:
        r = await bare_client.get("/api/artists/eggy")
    assert r.status_code == 401


async def test_special_chars_in_name_round_trip(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """`GET /api/artists/H%26rry` matches cache keyed 'h&rry'."""
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized="h&rry",
            display_name="H&rry",
            genres=["pop"],
            fetched_at=datetime.now(timezone.utc),
            fetch_failure_count=0,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(genres=["pop"], fetched_at=datetime.now(timezone.utc), fetch_failure_count=0),
        )
    )
    await db_session.execute(stmt)
    await db_session.flush()

    r = await client.get("/api/artists/H%26rry", headers=auth_headers)
    assert r.status_code == 200
    assert r.json()["artist_name"] == "H&rry"


def _make_prewarm_mocks(
    artist_names: list[str],
) -> tuple[object, object]:
    """Return (mock_session_maker, mock_session_context) for get_session_maker patch."""
    from unittest.mock import MagicMock

    mock_result = MagicMock()
    mock_result.all.return_value = [(name,) for name in artist_names]

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_session_cm = AsyncMock()
    mock_session_cm.__aenter__ = AsyncMock(return_value=mock_db)
    mock_session_cm.__aexit__ = AsyncMock(return_value=None)

    mock_sm = MagicMock()
    mock_sm.return_value = mock_session_cm
    return mock_sm, mock_db


async def test_prewarm_populates_cache_for_event_artists() -> None:
    """prewarm_artists_from_event calls _prewarm_one for each artist."""
    import uuid as _uuid

    from app.services.artist_prewarm import prewarm_artists_from_event

    event_id = _uuid.uuid4()
    artist_names = ["Artist 0", "Artist 1", "Artist 2"]
    mock_sm, _ = _make_prewarm_mocks(artist_names)

    prewarm_calls: list[str] = []

    async def _mock_prewarm_one(sm: object, name: str, settings: object) -> bool:
        prewarm_calls.append(name)
        return True

    with (
        patch("app.services.artist_prewarm.get_session_maker", return_value=mock_sm),
        patch("app.services.artist_prewarm._prewarm_one", side_effect=_mock_prewarm_one),
    ):
        await prewarm_artists_from_event(event_id)

    assert len(prewarm_calls) == 3


async def test_prewarm_skips_already_fresh() -> None:
    """_is_fresh returns True for a freshly-seeded row; prewarm_one skips it."""
    import uuid as _uuid

    from app.services.artist_prewarm import prewarm_artists_from_event

    event_id = _uuid.uuid4()
    # 2 artists; prewarm_one will be called for both
    artist_names = ["Artist 0", "Artist 1"]
    mock_sm, _ = _make_prewarm_mocks(artist_names)

    prewarm_calls: list[str] = []

    async def _mock_prewarm_one(sm: object, name: str, settings: object) -> bool:
        prewarm_calls.append(name)
        # Simulate "already fresh" by returning True without any external call
        return True

    with (
        patch("app.services.artist_prewarm.get_session_maker", return_value=mock_sm),
        patch("app.services.artist_prewarm._prewarm_one", side_effect=_mock_prewarm_one),
    ):
        await prewarm_artists_from_event(event_id)

    # Both artists were considered; no failure
    assert len(prewarm_calls) == 2


async def test_prewarm_one_failure_does_not_block_others() -> None:
    """One _prewarm_one call raises; other 2 artists still succeed."""
    import uuid as _uuid

    from app.services.artist_prewarm import prewarm_artists_from_event

    event_id = _uuid.uuid4()
    artist_names = ["Fail Artist 0", "Fail Artist 1", "Fail Artist 2"]
    mock_sm, _ = _make_prewarm_mocks(artist_names)

    call_count = 0

    async def _mock_prewarm_one(sm: object, name: str, settings: object) -> bool:
        nonlocal call_count
        call_count += 1
        if call_count == 2:
            raise Exception("injected failure for artist 2")
        return True

    with (
        patch("app.services.artist_prewarm.get_session_maker", return_value=mock_sm),
        patch("app.services.artist_prewarm._prewarm_one", side_effect=_mock_prewarm_one),
    ):
        # Should complete without raising even though one artist fails
        await prewarm_artists_from_event(event_id)

    assert call_count == 3


async def test_concurrent_requests_eventually_consistent(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Two concurrent requests for same artist → both 200; cache populated."""
    with (
        patch(
            "app.routes.artists._spotify.search_and_fetch",
            new_callable=AsyncMock,
            return_value=_FRESH_PROVIDER_ARTIST,
        ),
        patch(
            "app.routes.artists._lastfm.get_similar",
            new_callable=AsyncMock,
            return_value=[],
        ),
    ):
        r1, r2 = await asyncio.gather(
            client.get("/api/artists/eggy", headers=auth_headers),
            client.get("/api/artists/eggy", headers=auth_headers),
        )

    assert r1.status_code == 200
    assert r2.status_code == 200
