"""TASK-FE-ARTIST-SPOTIFY-LINK: unit tests for spotify_url derivation from artist.social_links."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist
from app.services.artist_normalize import normalize
from app.services.artist_service import _get_spotify_url


async def _insert_artist(
    db: AsyncSession,
    name: str,
    social_links: dict[str, object] | None,
) -> None:
    artist = Artist(
        artist_id=uuid.uuid4(),
        name=name,
        name_normalized=normalize(name),
        social_links=social_links,
    )
    db.add(artist)
    await db.flush()


async def test_spotify_url_populated_from_social_links(db_session: AsyncSession) -> None:
    await _insert_artist(
        db_session,
        "Spotify Link Artist",
        {"spotify": "https://open.spotify.com/artist/xyz"},
    )
    url = await _get_spotify_url(db_session, normalize("Spotify Link Artist"))
    assert url == "https://open.spotify.com/artist/xyz"


async def test_spotify_url_null_when_social_links_missing(db_session: AsyncSession) -> None:
    await _insert_artist(db_session, "No Social Links Artist", None)
    url = await _get_spotify_url(db_session, normalize("No Social Links Artist"))
    assert url is None


async def test_spotify_url_null_when_spotify_key_missing(db_session: AsyncSession) -> None:
    await _insert_artist(
        db_session,
        "Instagram Only Artist",
        {"instagram": "https://instagram.com/artist"},
    )
    url = await _get_spotify_url(db_session, normalize("Instagram Only Artist"))
    assert url is None
