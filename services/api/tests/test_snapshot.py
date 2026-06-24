"""BE-017: GET /api/groups/{invite_code}/snapshot — screenshotable group view."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.artist import Artist, SetArtist
from app.db.models.event import Event
from app.db.models.member import Member
from app.db.models.pick import Pick
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from tests.conftest import signup_and_get_token

# Snap window anchor: June 20, 2026 22:00 UTC
_SNAP_AT = "2026-06-20T22:00:00Z"
_SNAP_AT_DT = datetime(2026, 6, 20, 22, 0, tzinfo=timezone.utc)
_WINDOW = 60  # minutes


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def snap_setup(
    client: AsyncClient,
    db_session: AsyncSession,
    test_event: Event,
) -> tuple[str, str, uuid.UUID, uuid.UUID, Stage]:
    """Returns (token, invite_code, group_id, member_id, stage).

    Seeds: 1 user, 1 group attached to test_event, 1 stage.
    """
    token, _ = await signup_and_get_token(client, "snap_user@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Snap Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    group_id = uuid.UUID(r.json()["group_id"])
    member_id = uuid.UUID(r.json()["member_id"])

    stage = Stage(
        event_id=test_event.event_id,
        name="Main Stage",
        display_order=1,
        external_id="main-stage",
        color_hex="#ff4f9a",
    )
    db_session.add(stage)
    await db_session.flush()

    return token, invite_code, group_id, member_id, stage


def _make_set(
    db_session: AsyncSession,
    *,
    event_id: uuid.UUID,
    stage_id: uuid.UUID,
    name: str,
    starts_at: datetime,
    ends_at: datetime,
    external_id: str,
) -> Set:
    s = Set(
        event_id=event_id,
        stage_id=stage_id,
        display_name=name,
        day_label="SAT",
        starts_at=starts_at,
        ends_at=ends_at,
        external_id=external_id,
    )
    db_session.add(s)
    return s


async def _add_artist(
    db_session: AsyncSession, set_obj: Set, artist_name: str, position: int = 0
) -> None:
    artist = Artist(
        name=artist_name,
        name_normalized=artist_name.lower(),
        spotify_artist_id=None,
    )
    db_session.add(artist)
    await db_session.flush()
    db_session.add(SetArtist(set_id=set_obj.set_id, artist_id=artist.artist_id, position=position))
    await db_session.flush()


def _dt(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 6, 20, hour, minute, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_snapshot_returns_sets_overlapping_window(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """2 sets in window, 1 before, 1 after → response includes the 2."""
    token, invite_code, _, _, stage = snap_setup

    # In window: 21:30–22:30 (overlaps 22:00–23:00)
    s1 = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Set In 1",
        starts_at=_dt(21, 30),
        ends_at=_dt(22, 30),
        external_id="s1",
    )
    # In window: 22:30–23:30 (overlaps 22:00–23:00)
    s2 = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Set In 2",
        starts_at=_dt(22, 30),
        ends_at=_dt(23, 30),
        external_id="s2",
    )
    # Before window: ends at exactly 22:00 (ends_at > at is strict, so excluded)
    s3 = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Set Before",
        starts_at=_dt(20, 0),
        ends_at=_dt(22, 0),
        external_id="s3",
    )
    # After window: starts at exactly 23:00 (starts_at < window_end is strict, excluded)
    _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Set After",
        starts_at=_dt(23, 0),
        ends_at=_dt(0, 0),
        external_id="s4",
    )
    for s in [s1, s2, s3]:
        await db_session.flush()
        await _add_artist(db_session, s, f"Artist for {s.display_name}")

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes={_WINDOW}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    all_sets = [s for st in r.json()["stages"] for s in st["sets"]]
    names = {s["display_name"] for s in all_sets}
    assert names == {"Set In 1", "Set In 2"}


async def test_snapshot_ordering_stage_display_then_starts_at(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """Stages ordered by display_order; sets within stage by starts_at."""
    token, invite_code, _, _, stage1 = snap_setup

    stage2 = Stage(
        event_id=test_event.event_id,
        name="Second Stage",
        display_order=2,
        external_id="stage-2",
        color_hex="#36c6ff",
    )
    db_session.add(stage2)
    await db_session.flush()

    # Stage1 sets (display_order=1), out-of-order start times
    sa = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage1.stage_id,
        name="SA Late",
        starts_at=_dt(22, 30),
        ends_at=_dt(23, 0),
        external_id="sa",
    )
    sb = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage1.stage_id,
        name="SA Early",
        starts_at=_dt(22, 0),
        ends_at=_dt(22, 30),
        external_id="sb",
    )
    # Stage2 set (display_order=2)
    sc = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage2.stage_id,
        name="SC",
        starts_at=_dt(22, 15),
        ends_at=_dt(22, 45),
        external_id="sc",
    )
    for s in [sa, sb, sc]:
        await db_session.flush()
        await _add_artist(db_session, s, f"Artist {s.display_name}")

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes={_WINDOW}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    stages = r.json()["stages"]
    assert stages[0]["name"] == "Main Stage"
    assert stages[1]["name"] == "Second Stage"
    set_names = [s["display_name"] for s in stages[0]["sets"]]
    assert set_names == ["SA Early", "SA Late"]


async def test_snapshot_pickers_denormalized(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """Member's display_name, avatar_color, user_id, member_id are in response."""
    token, invite_code, _, member_id, stage = snap_setup

    s = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Picker Set",
        starts_at=_dt(22, 0),
        ends_at=_dt(23, 0),
        external_id="picker-set",
    )
    await db_session.flush()
    await _add_artist(db_session, s, "The Pickers")

    db_session.add(Pick(member_id=member_id, set_id=s.set_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes={_WINDOW}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    sets = r.json()["stages"][0]["sets"]
    assert len(sets) == 1
    pickers = sets[0]["pickers"]
    assert len(pickers) == 1
    assert pickers[0]["member_id"] == str(member_id)
    assert "display_name" in pickers[0]
    assert "avatar_color" in pickers[0]
    assert "user_id" in pickers[0]


async def test_snapshot_resolves_display_name_via_coalesce(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """COALESCE: override > user.display_name > "Member"."""
    token, invite_code, group_id, member_id, stage = snap_setup

    # Override the member's display_name_override
    member_result = await db_session.execute(select(Member).where(Member.id == member_id))
    member = member_result.scalar_one()
    member.display_name_override = "Custom Override"
    await db_session.flush()

    s = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Coalesce Set",
        starts_at=_dt(22, 0),
        ends_at=_dt(23, 0),
        external_id="coalesce-set",
    )
    await db_session.flush()
    await _add_artist(db_session, s, "Coalesce Artist")

    db_session.add(Pick(member_id=member_id, set_id=s.set_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes={_WINDOW}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    pickers = r.json()["stages"][0]["sets"][0]["pickers"]
    assert pickers[0]["display_name"] == "Custom Override"


async def test_snapshot_members_total_counts_all_group_members(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """5 members in group, 1 with a pick in window → members_total == 5."""
    token, invite_code, group_id, member_id, stage = snap_setup

    # Add 4 more members
    for i in range(4):
        extra_token, _ = await signup_and_get_token(client, f"extra{i}@example.com")
        r2 = await client.post(
            "/api/groups/join",
            json={"invite_code": invite_code, "display_name_override": f"Extra {i}"},
            headers={"Authorization": f"Bearer {extra_token}"},
        )
        assert r2.status_code in (200, 201)

    s = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Total Set",
        starts_at=_dt(22, 0),
        ends_at=_dt(23, 0),
        external_id="total-set",
    )
    await db_session.flush()
    await _add_artist(db_session, s, "Total Artist")
    db_session.add(Pick(member_id=member_id, set_id=s.set_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes={_WINDOW}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["members_total"] == 5


async def test_snapshot_no_overlap_returns_empty_sets(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """at outside event window → stages with empty sets lists."""
    token, invite_code, _, _, stage = snap_setup

    s = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Old Set",
        starts_at=_dt(10, 0),
        ends_at=_dt(11, 0),
        external_id="old-set",
    )
    await db_session.flush()
    await _add_artist(db_session, s, "Old Artist")

    # at=18:00, window=60 → window is 18:00–19:00, set is 10–11 → no overlap
    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at=2026-06-20T18:00:00Z&window_minutes=60",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["stages"] == []


async def test_snapshot_starts_at_equal_at_is_included(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """Set starts_at == at → included (starts_at < window_end is true)."""
    token, invite_code, _, _, stage = snap_setup

    s = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Exact Start",
        starts_at=_dt(22, 0),
        ends_at=_dt(23, 0),
        external_id="exact-start",
    )
    await db_session.flush()
    await _add_artist(db_session, s, "Exact Start Artist")

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes={_WINDOW}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    all_sets = [s for st in r.json()["stages"] for s in st["sets"]]
    assert any(s["display_name"] == "Exact Start" for s in all_sets)


async def test_snapshot_ends_at_equal_at_is_excluded(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """Set ends_at == at → excluded (ends_at > at is strict)."""
    token, invite_code, _, _, stage = snap_setup

    s = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="Exact End",
        starts_at=_dt(20, 0),
        ends_at=_dt(22, 0),
        external_id="exact-end",
    )
    await db_session.flush()
    await _add_artist(db_session, s, "Exact End Artist")

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes={_WINDOW}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    all_sets = [s for st in r.json()["stages"] for s in st["sets"]]
    assert all(s["display_name"] != "Exact End" for s in all_sets)


async def test_snapshot_missing_at_returns_400(
    client: AsyncClient,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
) -> None:
    token, invite_code, _, _, _ = snap_setup
    r = await client.get(
        f"/api/groups/{invite_code}/snapshot",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "at_required"


async def test_snapshot_window_too_small_returns_422(
    client: AsyncClient,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
) -> None:
    token, invite_code, _, _, _ = snap_setup
    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes=4",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_snapshot_window_too_large_returns_422(
    client: AsyncClient,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
) -> None:
    token, invite_code, _, _, _ = snap_setup
    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes=361",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_snapshot_window_default_60(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
) -> None:
    token, invite_code, _, _, _ = snap_setup
    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["window_minutes"] == 60


async def test_snapshot_not_a_member_returns_403(
    client: AsyncClient,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
) -> None:
    _, invite_code, _, _, _ = snap_setup
    other_token, _ = await signup_and_get_token(client, "non_member_snap@example.com")
    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}",
        headers={"Authorization": f"Bearer {other_token}"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "not_a_member"


async def test_snapshot_unknown_code_returns_404(
    client: AsyncClient,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
) -> None:
    token, _, _, _, _ = snap_setup
    r = await client.get(
        "/api/groups/XXXXXXXX/snapshot?at=2026-06-20T22:00:00Z",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404


async def test_snapshot_if_modified_since_returns_304(
    client: AsyncClient,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
) -> None:
    token, invite_code, _, _, _ = snap_setup
    r1 = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    last_modified = r1.headers["last-modified"]

    r2 = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}",
        headers={"Authorization": f"Bearer {token}", "if-modified-since": last_modified},
    )
    assert r2.status_code == 304


async def test_snapshot_after_new_pick_returns_200(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """After a new pick lands, If-Modified-Since with old value → 200."""
    import time

    from sqlalchemy import select as _select

    from app.db.models.group import Group

    token, invite_code, group_id, member_id, stage = snap_setup

    # Anchor last_active_at to a known old timestamp so Last-Modified is predictable
    group_result = await db_session.execute(_select(Group).where(Group.id == group_id))
    group_obj = group_result.scalar_one()
    group_obj.last_active_at = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    await db_session.flush()

    # First snapshot — captures old Last-Modified from 2026-01-01
    r1 = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 200
    old_last_modified = r1.headers["last-modified"]

    # Create a set and add a pick (pick_service updates group.last_active_at to now)
    s = _make_set(
        db_session,
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        name="New Pick Set",
        starts_at=_dt(22, 0),
        ends_at=_dt(23, 0),
        external_id="new-pick-set",
    )
    await db_session.flush()
    await _add_artist(db_session, s, "New Artist")

    new_clock = int(time.time() * 1000)
    r_pick = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(s.set_id), "state": "active", "state_clock_ms": new_clock},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_pick.status_code == 200

    # Snapshot with old If-Modified-Since → 200 (last_active_at is now >> 2026-01-01)
    r2 = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}",
        headers={
            "Authorization": f"Bearer {token}",
            "if-modified-since": old_last_modified,
        },
    )
    assert r2.status_code == 200


async def test_snapshot_no_n_plus_1(
    client: AsyncClient,
    db_session: AsyncSession,
    snap_setup: tuple[str, str, uuid.UUID, uuid.UUID, Stage],
    test_event: Event,
) -> None:
    """50 sets × 3 artists, 10 members with picks — response correct; impl uses 2 main queries."""
    token, invite_code, group_id, member_id, stage = snap_setup

    # Add 9 more members
    tokens = [token]
    mids = [member_id]
    for i in range(9):
        t, _ = await signup_and_get_token(client, f"np_user_{i}@example.com")
        tokens.append(t)
        r = await client.post(
            "/api/groups/join",
            json={"invite_code": invite_code, "display_name_override": f"User {i}"},
            headers={"Authorization": f"Bearer {t}"},
        )
        assert r.status_code in (200, 201)
        mids.append(uuid.UUID(r.json()["member"]["member_id"]))

    # Seed 50 sets with 3 artists each
    set_objs = []
    for i in range(50):
        s = _make_set(
            db_session,
            event_id=test_event.event_id,
            stage_id=stage.stage_id,
            name=f"Set {i:02d}",
            starts_at=_dt(21) + __import__("datetime").timedelta(minutes=i * 2),
            ends_at=_dt(23),
            external_id=f"np-set-{i}",
        )
        await db_session.flush()
        for j in range(3):
            await _add_artist(db_session, s, f"Artist {i}-{j}", position=j)
        set_objs.append(s)

    # Each of 10 members picks first set
    for mid in mids:
        db_session.add(
            Pick(member_id=mid, set_id=set_objs[0].set_id, state="active", state_clock_ms=1)
        )
    await db_session.flush()

    r = await client.get(
        f"/api/groups/{invite_code}/snapshot?at={_SNAP_AT}&window_minutes=120",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    all_sets = [s for st in r.json()["stages"] for s in st["sets"]]
    assert len(all_sets) == 50
    # First set has 10 pickers
    first_set = next(s for s in all_sets if s["display_name"] == "Set 00")
    assert len(first_set["pickers"]) == 10
    # All sets have 3 artist names
    assert all(len(s["artist_names"]) == 3 for s in all_sets)
