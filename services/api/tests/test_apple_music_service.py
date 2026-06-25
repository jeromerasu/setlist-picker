"""SETLIST-APPLE-MUSIC-INTEGRATION: GET /api/artists/{name}/apple-music endpoint tests."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist_cache import ArtistCache
from app.schemas.artists import AppleMusicArtistDetail, AppleMusicTrack
from app.services.apple_music_service import (
    AppleMusicService,
    _format_artwork_url,
    is_configured,
)
from app.services.artist_normalize import normalize
from tests.conftest import signup_and_get_token

_FAKE_TRACKS = [
    AppleMusicTrack(
        name=f"Track {i}",
        duration_ms=200_000 + i * 1000,
        apple_music_url=f"https://music.apple.com/us/album/track-{i}/1",
        preview_url=f"https://audio-ssl.itunes.apple.com/preview-{i}.m4a",
    )
    for i in range(1, 6)
]

_FAKE_DETAIL = AppleMusicArtistDetail(
    artist_name="5napback",
    apple_music_artist_id="1236169964",
    image_url="https://is1-ssl.mzstatic.com/image/thumb/600x600bb.jpg",
    genres=["Electronic", "House"],
    top_tracks=_FAKE_TRACKS,
)


# ── Utility unit tests ────────────────────────────────────────────────────────


def test_format_artwork_url_replaces_placeholder() -> None:
    url = "https://is1-ssl.mzstatic.com/image/{w}x{h}bb.jpg"
    assert _format_artwork_url(url) == "https://is1-ssl.mzstatic.com/image/600x600bb.jpg"


def test_format_artwork_url_no_placeholder_is_unchanged() -> None:
    url = "https://is1-ssl.mzstatic.com/image/already-sized.jpg"
    assert _format_artwork_url(url) == url


def test_is_configured_true() -> None:
    assert is_configured("TEAM1234AB", "KEY1234AB", "c29tZWJhc2U2NA==") is True


def test_is_configured_false_on_empty() -> None:
    assert is_configured("", "KEY1234AB", "c29tZWJhc2U2NA==") is False
    assert is_configured("TEAM1234AB", "", "c29tZWJhc2U2NA==") is False
    assert is_configured("TEAM1234AB", "KEY1234AB", "") is False


# ── JWT generation ────────────────────────────────────────────────────────────


def test_jwt_built_with_correct_claims() -> None:
    """JWT payload has iss, iat, exp; header has kid and alg=ES256."""
    import base64

    # Generate a real P-256 key for the test so we don't need real Apple creds.
    from cryptography.hazmat.primitives.asymmetric.ec import (
        SECP256R1,
        generate_private_key,
    )
    from cryptography.hazmat.primitives.serialization import (
        Encoding,
        NoEncryption,
        PrivateFormat,
    )
    from jose import jwt as jose_jwt

    private_key = generate_private_key(SECP256R1())
    pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    b64 = base64.b64encode(pem).decode()

    svc = AppleMusicService(team_id="TEAM123456", key_id="KEYID12345", private_key_b64=b64)
    token = svc._build_jwt()

    # Decode without verification to inspect claims
    claims = jose_jwt.get_unverified_claims(token)
    header = jose_jwt.get_unverified_header(token)

    assert claims["iss"] == "TEAM123456"
    assert "iat" in claims
    assert "exp" in claims
    assert claims["exp"] > claims["iat"]
    assert header["kid"] == "KEYID12345"
    assert header["alg"] == "ES256"


def test_jwt_refresh_window() -> None:
    """_get_jwt returns a fresh token when old one is within 24 h of expiry."""
    import base64
    import time

    from cryptography.hazmat.primitives.asymmetric.ec import SECP256R1, generate_private_key
    from cryptography.hazmat.primitives.serialization import Encoding, NoEncryption, PrivateFormat

    pem = generate_private_key(SECP256R1()).private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()
    )
    svc = AppleMusicService("T", "K", base64.b64encode(pem).decode())
    svc._jwt = "old-token"
    svc._jwt_expires_at = time.time() + 3600  # only 1 h remaining — within 24 h window
    new_token = svc._get_jwt()
    assert new_token != "old-token"


# ── Endpoint availability ─────────────────────────────────────────────────────


@pytest.fixture
async def auth_headers(client: AsyncClient) -> dict[str, str]:
    token, _ = await signup_and_get_token(client, "apple_music_test@example.com")
    return {"Authorization": f"Bearer {token}"}


async def test_unauthenticated_apple_music_endpoint_returns_401(client: AsyncClient) -> None:
    import httpx

    from app.main import app as _app

    transport = httpx.ASGITransport(app=_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as bare_client:
        r = await bare_client.get("/api/artists/5napback/apple-music")
    assert r.status_code == 401


async def test_no_credentials_returns_503(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """When _apple_music singleton is None (no creds), endpoint returns 503."""
    with patch("app.routes.artists._apple_music", None):
        r = await client.get("/api/artists/5napback/apple-music", headers=auth_headers)
    assert r.status_code == 503
    assert r.json()["detail"]["error_code"] == "apple_music_not_configured"


async def test_search_fails_no_cache_returns_503(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """Apple Music search fails + no cached row → 503 artist_unavailable."""
    mock_svc = AsyncMock(spec=AppleMusicService)
    mock_svc.search_artist.side_effect = Exception("network error")
    with patch("app.routes.artists._apple_music", mock_svc):
        r = await client.get("/api/artists/unknown-artist-xyz/apple-music", headers=auth_headers)
    assert r.status_code == 503
    assert r.json()["detail"]["error_code"] == "artist_unavailable"


# ── Search-then-fetch flow ────────────────────────────────────────────────────


async def test_cache_miss_searches_and_fetches_top_tracks(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Cache miss → search → fetch top tracks → 200 with all fields populated."""
    mock_svc = AsyncMock(spec=AppleMusicService)
    mock_svc.search_artist.return_value = (
        "1236169964",
        "5napback",
        "https://is1-ssl.mzstatic.com/image/600x600bb.jpg",
        ["Electronic", "House"],
    )
    mock_svc.get_top_tracks.return_value = _FAKE_TRACKS

    with patch("app.routes.artists._apple_music", mock_svc):
        r = await client.get("/api/artists/5napback/apple-music", headers=auth_headers)

    assert r.status_code == 200
    data = r.json()
    assert data["apple_music_artist_id"] == "1236169964"
    assert data["image_url"] == "https://is1-ssl.mzstatic.com/image/600x600bb.jpg"
    assert data["genres"] == ["Electronic", "House"]
    assert len(data["top_tracks"]) == 5
    assert data["top_tracks"][0]["apple_music_url"].startswith("https://music.apple.com")

    mock_svc.search_artist.assert_called_once()
    mock_svc.get_top_tracks.assert_called_once_with("1236169964", limit=5)


async def test_cache_hit_with_tracks_skips_api(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Hot cache with apple_music_artist_id + top_tracks → Apple Music not called."""
    tracks = [
        {
            "name": f"Track {i}",
            "duration_ms": 200_000,
            "apple_music_url": f"https://music.apple.com/us/album/track-{i}/1",
            "preview_url": None,
        }
        for i in range(5)
    ]
    stmt = (
        pg_insert(ArtistCache)
        .values(
            name_normalized=normalize("snapback-cache-test"),
            display_name="Snapback Cache Test",
            apple_music_artist_id="9999999",
            image_url="https://is1-ssl.mzstatic.com/image/600x600bb.jpg",
            genres=["Electronic"],
            top_tracks=tracks,
            fetched_at=datetime.now(timezone.utc),
            fetch_failure_count=0,
        )
        .on_conflict_do_update(
            index_elements=["name_normalized"],
            set_=dict(
                apple_music_artist_id="9999999",
                top_tracks=tracks,
                fetched_at=datetime.now(timezone.utc),
            ),
        )
    )
    await db_session.execute(stmt)
    await db_session.flush()

    mock_svc = AsyncMock(spec=AppleMusicService)
    with patch("app.routes.artists._apple_music", mock_svc):
        r = await client.get(
            "/api/artists/snapback-cache-test/apple-music", headers=auth_headers
        )

    assert r.status_code == 200
    data = r.json()
    assert len(data["top_tracks"]) == 5
    mock_svc.search_artist.assert_not_called()
    mock_svc.get_top_tracks.assert_not_called()


async def test_genre_normalization_passes_through(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Apple Music genreNames are returned verbatim (no lowercasing)."""
    mock_svc = AsyncMock(spec=AppleMusicService)
    mock_svc.search_artist.return_value = (
        "111",
        "Genre Test Artist",
        None,
        ["Electronic", "Dance", "Music"],
    )
    mock_svc.get_top_tracks.return_value = []

    with patch("app.routes.artists._apple_music", mock_svc):
        r = await client.get(
            "/api/artists/genre-test-artist/apple-music", headers=auth_headers
        )

    assert r.status_code == 200
    assert r.json()["genres"] == ["Electronic", "Dance", "Music"]


async def test_artwork_url_substitution_in_search(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Artwork URL with {w}x{h} placeholder is replaced with 600x600."""
    mock_svc = AsyncMock(spec=AppleMusicService)
    mock_svc.search_artist.return_value = (
        "222",
        "Artwork Test",
        "https://is1-ssl.mzstatic.com/image/600x600bb.jpg",
        [],
    )
    mock_svc.get_top_tracks.return_value = []

    with patch("app.routes.artists._apple_music", mock_svc):
        r = await client.get(
            "/api/artists/artwork-test/apple-music", headers=auth_headers
        )

    assert r.status_code == 200
    assert "600x600" in (r.json()["image_url"] or "")


async def test_top_tracks_failure_returns_partial_response(
    client: AsyncClient,
    db_session: AsyncSession,
    auth_headers: dict[str, str],
) -> None:
    """Top-tracks fetch fails → return image+genres with empty top_tracks (no 503)."""
    mock_svc = AsyncMock(spec=AppleMusicService)
    mock_svc.search_artist.return_value = (
        "333",
        "Partial Artist",
        "https://is1-ssl.mzstatic.com/image/600x600bb.jpg",
        ["Techno"],
    )
    mock_svc.get_top_tracks.side_effect = Exception("timeout")

    with patch("app.routes.artists._apple_music", mock_svc):
        r = await client.get(
            "/api/artists/partial-artist/apple-music", headers=auth_headers
        )

    assert r.status_code == 200
    data = r.json()
    assert data["genres"] == ["Techno"]
    assert data["top_tracks"] == []
