"""BE-012: GET /api/events list + search."""

from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from tests.conftest import signup_and_get_token


@pytest.fixture
async def seed_events(db_session: AsyncSession) -> list[Event]:
    events = [
        Event(
            name="EDC Las Vegas 2026",
            start_date=date(2026, 5, 15),
            end_date=date(2026, 5, 17),
            location="Las Vegas, NV",
            timezone="America/Los_Angeles",
            source_adapter="manual",
        ),
        Event(
            name="Tomorrowland 2026 W1",
            start_date=date(2026, 7, 17),
            end_date=date(2026, 7, 19),
            location="Boom, Belgium",
            timezone="Europe/Brussels",
            source_adapter="manual",
        ),
        Event(
            name="Ultra Music Festival 2026",
            start_date=date(2026, 3, 27),
            end_date=date(2026, 3, 29),
            location="Miami, FL",
            timezone="America/New_York",
            source_adapter="manual",
        ),
    ]
    for e in events:
        db_session.add(e)
    await db_session.flush()
    return events


async def test_list_events_no_query_returns_all_sorted(
    client: AsyncClient, seed_events: list[Event]
) -> None:
    token, _ = await signup_and_get_token(client, "evtuser1@example.com")
    r = await client.get("/api/events", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) == 3
    dates = [e["start_date"] for e in events]
    assert dates == sorted(dates)


async def test_list_events_query_matches_name(
    client: AsyncClient, seed_events: list[Event]
) -> None:
    token, _ = await signup_and_get_token(client, "evtuser2@example.com")
    r = await client.get("/api/events?q=EDC", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) == 1
    assert "EDC" in events[0]["name"]


async def test_list_events_query_matches_location(
    client: AsyncClient, seed_events: list[Event]
) -> None:
    token, _ = await signup_and_get_token(client, "evtuser3@example.com")
    r = await client.get("/api/events?q=Las Vegas", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
    events = r.json()["events"]
    assert len(events) == 1
    assert events[0]["location"] == "Las Vegas, NV"


async def test_list_events_query_case_insensitive(
    client: AsyncClient, seed_events: list[Event]
) -> None:
    token, _ = await signup_and_get_token(client, "evtuser4@example.com")
    r1 = await client.get("/api/events?q=edc", headers={"authorization": f"Bearer {token}"})
    r2 = await client.get("/api/events?q=EDC", headers={"authorization": f"Bearer {token}"})
    assert r1.status_code == r2.status_code == 200
    assert len(r1.json()["events"]) == 1
    assert r1.json()["events"] == r2.json()["events"]


async def test_list_events_empty_query_returns_all(
    client: AsyncClient, seed_events: list[Event]
) -> None:
    token, _ = await signup_and_get_token(client, "evtuser5@example.com")
    r1 = await client.get("/api/events?q=", headers={"authorization": f"Bearer {token}"})
    r2 = await client.get(
        "/api/events", params={"q": "   "}, headers={"authorization": f"Bearer {token}"}
    )
    assert r1.status_code == r2.status_code == 200
    assert len(r1.json()["events"]) == 3
    assert len(r2.json()["events"]) == 3


async def test_list_events_no_match_returns_empty(
    client: AsyncClient, seed_events: list[Event]
) -> None:
    token, _ = await signup_and_get_token(client, "evtuser6@example.com")
    r = await client.get("/api/events?q=zzz", headers={"authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["events"] == []


async def test_list_events_sql_wildcard_in_query_is_literal(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    # "50 Cent Fan Fest" contains "50" but NOT "50%"
    # If % is NOT escaped, pattern "%50%%" matches "50 Cent Fan Fest" (because "50" is there)
    # If % IS escaped, pattern "%50\%%" only matches strings containing literal "50%"
    event = Event(
        name="50 Cent Fan Fest",
        start_date=date(2026, 8, 1),
        end_date=date(2026, 8, 1),
        location="Detroit, MI",
        timezone="America/Detroit",
        source_adapter="manual",
    )
    db_session.add(event)
    await db_session.flush()

    token, _ = await signup_and_get_token(client, "evtuser7@example.com")
    r = await client.get(
        "/api/events", params={"q": "50%"}, headers={"authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["events"] == []


async def test_list_events_unauthenticated_returns_401(
    client: AsyncClient, seed_events: list[Event]
) -> None:
    r = await client.get("/api/events")
    assert r.status_code == 401
