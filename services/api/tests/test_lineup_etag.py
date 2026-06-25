"""TASK-SETLIST-PERF-CONFIG: ETag + 304 on GET /api/events/{id}/lineup."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from tests.conftest import signup_and_get_token


@pytest.fixture
async def etag_event(db_session: AsyncSession) -> Event:
    event = Event(
        name="ETag Test Fest",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 3),
        location="Test City",
        timezone="UTC",
        source_adapter="manual",
        imported_at=datetime(2026, 8, 1, 10, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(event)
    await db_session.flush()
    return event


async def test_first_request_returns_200_with_etag(
    client: AsyncClient,
    db_session: AsyncSession,
    etag_event: Event,
) -> None:
    token, _ = await signup_and_get_token(client, "etag1@example.com")
    r = await client.get(
        f"/api/events/{etag_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert "etag" in r.headers
    etag = r.headers["etag"]
    assert etag.startswith('"') and etag.endswith('"')
    assert len(etag) == 18  # '"' + 16 chars + '"'


async def test_matching_if_none_match_returns_304(
    client: AsyncClient,
    db_session: AsyncSession,
    etag_event: Event,
) -> None:
    token, _ = await signup_and_get_token(client, "etag2@example.com")
    r1 = await client.get(
        f"/api/events/{etag_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    etag = r1.headers["etag"]

    r2 = await client.get(
        f"/api/events/{etag_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}", "if-none-match": etag},
    )
    assert r2.status_code == 304
    assert r2.content == b""


async def test_etag_changes_after_event_updated_at_changes(
    client: AsyncClient,
    db_session: AsyncSession,
    etag_event: Event,
) -> None:
    token, _ = await signup_and_get_token(client, "etag3@example.com")
    r1 = await client.get(
        f"/api/events/{etag_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    etag_before = r1.headers["etag"]

    # Simulate a lineup re-import by bumping imported_at
    etag_event.imported_at = etag_event.imported_at + timedelta(seconds=1)
    await db_session.flush()

    r2 = await client.get(
        f"/api/events/{etag_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.headers["etag"] != etag_before
