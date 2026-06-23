"""BE-013: GET /api/events/{event_id}/lineup — stages + sets + artists."""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist, SetArtist
from app.db.models.event import Event
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from tests.conftest import signup_and_get_token


@pytest.fixture
async def lineup_event(db_session: AsyncSession) -> Event:
    event = Event(
        name="Lineup Fest 2026",
        start_date=date(2026, 9, 25),
        end_date=date(2026, 9, 27),
        location="Boom, Belgium",
        timezone="Europe/Brussels",
        source_adapter="event_api_v1",
    )
    db_session.add(event)
    await db_session.flush()
    return event


async def _make_stage(
    db: AsyncSession, event_id: uuid.UUID, name: str, display_order: int
) -> Stage:
    stage = Stage(
        event_id=event_id, name=name, display_order=display_order, external_id=name.lower()
    )
    db.add(stage)
    await db.flush()
    return stage


async def _make_artist(db: AsyncSession, name: str) -> Artist:
    from app.services.artist_normalize import normalize

    artist = Artist(
        name=name,
        name_normalized=normalize(name),
        spotify_artist_id=None,
    )
    db.add(artist)
    await db.flush()
    return artist


async def _make_set(
    db: AsyncSession,
    event_id: uuid.UUID,
    stage_id: uuid.UUID,
    display_name: str,
    starts_at: datetime,
    ends_at: datetime,
    artists: list[Artist],
) -> Set:
    s = Set(
        event_id=event_id,
        stage_id=stage_id,
        display_name=display_name,
        day_label="FRIDAY",
        starts_at=starts_at,
        ends_at=ends_at,
        external_id=display_name.lower().replace(" ", "-"),
    )
    db.add(s)
    await db.flush()
    for pos, art in enumerate(artists):
        sa = SetArtist(set_id=s.set_id, artist_id=art.artist_id, position=pos)
        db.add(sa)
    await db.flush()
    return s


def _ts(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 9, 25, hour, minute, tzinfo=timezone.utc)


async def test_get_lineup_returns_event_summary_stages_sets(
    client: AsyncClient, db_session: AsyncSession, lineup_event: Event
) -> None:
    stage_a = await _make_stage(db_session, lineup_event.event_id, "Main Stage", 1)
    stage_b = await _make_stage(db_session, lineup_event.event_id, "Second Stage", 2)
    art1 = await _make_artist(db_session, "Artist One")
    art2 = await _make_artist(db_session, "Artist Two")
    art3 = await _make_artist(db_session, "Artist Three")
    eid = lineup_event.event_id
    await _make_set(db_session, eid, stage_a.stage_id, "Set A", _ts(14), _ts(15), [art1])
    await _make_set(db_session, eid, stage_a.stage_id, "Set B", _ts(16), _ts(17), [art2])
    await _make_set(db_session, eid, stage_b.stage_id, "Set C", _ts(18), _ts(19), [art3])

    token, _ = await signup_and_get_token(client, "lineup1")
    r = await client.get(
        f"/api/events/{lineup_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["event_id"] == str(lineup_event.event_id)
    assert len(body["stages"]) == 2
    assert len(body["sets"]) == 3


async def test_get_lineup_orders_stages_by_display_order(
    client: AsyncClient, db_session: AsyncSession, lineup_event: Event
) -> None:
    await _make_stage(db_session, lineup_event.event_id, "Stage C", 3)
    await _make_stage(db_session, lineup_event.event_id, "Stage A", 1)
    await _make_stage(db_session, lineup_event.event_id, "Stage B", 2)

    token, _ = await signup_and_get_token(client, "lineup2")
    r = await client.get(
        f"/api/events/{lineup_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    orders = [s["display_order"] for s in r.json()["stages"]]
    assert orders == sorted(orders)


async def test_get_lineup_orders_sets_by_starts_at(
    client: AsyncClient, db_session: AsyncSession, lineup_event: Event
) -> None:
    stage = await _make_stage(db_session, lineup_event.event_id, "Stage X", 1)
    art = await _make_artist(db_session, "DJ Test")
    eid = lineup_event.event_id
    sid = stage.stage_id
    await _make_set(db_session, eid, sid, "Late Set", _ts(22), _ts(23), [art])
    await _make_set(db_session, eid, sid, "Early Set", _ts(12), _ts(13), [art])
    await _make_set(db_session, eid, sid, "Mid Set", _ts(17), _ts(18), [art])

    token, _ = await signup_and_get_token(client, "lineup3")
    r = await client.get(
        f"/api/events/{lineup_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    names = [s["display_name"] for s in r.json()["sets"]]
    assert names == ["Early Set", "Mid Set", "Late Set"]


async def test_get_lineup_includes_artists_per_set(
    client: AsyncClient, db_session: AsyncSession, lineup_event: Event
) -> None:
    stage = await _make_stage(db_session, lineup_event.event_id, "B2B Stage", 1)
    art_a = await _make_artist(db_session, "B2B Artist A")
    art_b = await _make_artist(db_session, "B2B Artist B")
    art_c = await _make_artist(db_session, "B2B Artist C")
    await _make_set(
        db_session,
        lineup_event.event_id,
        stage.stage_id,
        "B2B Set",
        _ts(20),
        _ts(21),
        [art_a, art_b, art_c],
    )

    token, _ = await signup_and_get_token(client, "lineup4")
    r = await client.get(
        f"/api/events/{lineup_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    sets = r.json()["sets"]
    assert len(sets) == 1
    artists = sets[0]["artists"]
    assert len(artists) == 3
    positions = [a["position"] for a in artists]
    assert positions == sorted(positions)


async def test_get_lineup_missing_event_returns_404(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    token, _ = await signup_and_get_token(client, "lineup5")
    r = await client.get(
        f"/api/events/{uuid.uuid4()}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "event_not_found"


async def test_get_lineup_handles_midnight_straddle(
    client: AsyncClient, db_session: AsyncSession, lineup_event: Event
) -> None:
    stage = await _make_stage(db_session, lineup_event.event_id, "Night Stage", 1)
    art = await _make_artist(db_session, "Midnight DJ")
    starts = datetime(2026, 9, 25, 23, 0, tzinfo=timezone.utc)
    ends = datetime(2026, 9, 26, 1, 0, tzinfo=timezone.utc)
    await _make_set(
        db_session, lineup_event.event_id, stage.stage_id, "Midnight Set", starts, ends, [art]
    )

    token, _ = await signup_and_get_token(client, "lineup6")
    r = await client.get(
        f"/api/events/{lineup_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    s = r.json()["sets"][0]
    assert s["display_name"] == "Midnight Set"
    assert "23:00" in s["starts_at"]
    assert "01:00" in s["ends_at"]


async def test_get_lineup_unauthenticated_returns_401(
    client: AsyncClient, lineup_event: Event
) -> None:
    r = await client.get(f"/api/events/{lineup_event.event_id}/lineup")
    assert r.status_code == 401


async def test_get_lineup_no_n_plus_1(
    client: AsyncClient, db_session: AsyncSession, lineup_event: Event
) -> None:
    """Service uses a single JOIN for sets+artists — verify correctness for 10 sets × 3 artists."""
    stage = await _make_stage(db_session, lineup_event.event_id, "Big Stage", 1)
    for i in range(10):
        artists = [await _make_artist(db_session, f"Artist {i}-{j}") for j in range(3)]
        await _make_set(
            db_session,
            lineup_event.event_id,
            stage.stage_id,
            f"Set {i}",
            _ts(12 + i),
            _ts(13 + i),
            artists,
        )

    token, _ = await signup_and_get_token(client, "lineup7")
    r = await client.get(
        f"/api/events/{lineup_event.event_id}/lineup",
        headers={"authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    sets = r.json()["sets"]
    assert len(sets) == 10
    for s in sets:
        assert len(s["artists"]) == 3
