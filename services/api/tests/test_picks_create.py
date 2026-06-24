"""BE-015: POST /api/groups/{invite_code}/picks — LWW upsert tests."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from app.db.models.group import Group
from app.db.models.group_activity import GroupActivity
from app.db.models.pick import Pick
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from tests.conftest import signup_and_get_token


@pytest.fixture
async def pick_setup(
    client: AsyncClient,
    db_session: AsyncSession,
    test_event: Event,
) -> tuple[str, str, str, uuid.UUID, uuid.UUID]:
    """Returns (token, invite_code, group_id, member_id, set_id)."""
    token, _ = await signup_and_get_token(client, "pick_user@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Pick Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    group_id = uuid.UUID(r.json()["group_id"])
    member_id = uuid.UUID(r.json()["member_id"])

    stage = Stage(
        event_id=test_event.event_id,
        name="Main",
        display_order=1,
        external_id="main",
        color_hex="#ff4f9a",
    )
    db_session.add(stage)
    await db_session.flush()

    s = Set(
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        display_name="Great Set",
        day_label="SAT",
        starts_at=datetime(2026, 6, 20, 20, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 20, 21, 0, tzinfo=timezone.utc),
        external_id="great-set",
    )
    db_session.add(s)
    await db_session.flush()

    return token, invite_code, str(group_id), member_id, s.set_id


def _now_ms() -> int:
    return int(time.time() * 1000)


async def test_first_pick_creates_row_and_activity(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, _, member_id, set_id = pick_setup
    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": _now_ms()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["accepted"] is True
    assert body["state"] == "active"

    pick = (
        await db_session.execute(
            select(Pick).where(Pick.member_id == member_id, Pick.set_id == set_id)
        )
    ).scalar_one()
    assert pick.state == "active"

    activity = (
        await db_session.execute(select(GroupActivity).where(GroupActivity.kind == "pick_added"))
    ).scalar_one()
    assert activity is not None


async def test_unpick_writes_tombstoned_state_and_activity(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, _, member_id, set_id = pick_setup
    now = _now_ms()
    await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": now},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "tombstoned", "state_clock_ms": now + 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["state"] == "tombstoned"
    assert r.json()["accepted"] is True

    pick = (
        await db_session.execute(
            select(Pick).where(Pick.member_id == member_id, Pick.set_id == set_id)
        )
    ).scalar_one()
    assert pick.state == "tombstoned"

    removed_activity = (
        await db_session.execute(select(GroupActivity).where(GroupActivity.kind == "pick_removed"))
    ).scalar_one_or_none()
    assert removed_activity is not None


async def test_pick_same_state_no_activity_written(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, _, _, set_id = pick_setup
    now = _now_ms()
    await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": now},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": now + 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    activities = (
        (await db_session.execute(select(GroupActivity).where(GroupActivity.kind == "pick_added")))
        .scalars()
        .all()
    )
    # Only one activity row (from the first pick_added); second POST is same state (active→active)
    assert len(activities) == 1


async def test_lww_loss_returns_accepted_false(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, _, member_id, set_id = pick_setup
    # Seed with high clock
    db_session.add(Pick(member_id=member_id, set_id=set_id, state="active", state_clock_ms=2000))
    await db_session.flush()

    # POST with lower clock → LWW loss
    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "tombstoned", "state_clock_ms": 1000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["accepted"] is False

    pick = (
        await db_session.execute(
            select(Pick).where(Pick.member_id == member_id, Pick.set_id == set_id)
        )
    ).scalar_one()
    assert pick.state == "active"
    assert pick.state_clock_ms == 2000


async def test_clock_skew_beyond_buffer_returns_400(
    client: AsyncClient,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, _, _, set_id = pick_setup
    future_clock = _now_ms() + 7_200_000  # 2 hours in future
    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": future_clock},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 400
    assert r.json()["detail"]["error_code"] == "pick_clock_skew_rejected"


async def test_set_in_different_event_returns_404(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
    test_event: Event,
) -> None:
    token, invite_code, _, _, _ = pick_setup
    other_event = Event(
        name="Other Fest",
        start_date=test_event.start_date,
        end_date=test_event.end_date,
        timezone="UTC",
        source_adapter="manual",
    )
    db_session.add(other_event)
    await db_session.flush()

    other_stage = Stage(
        event_id=other_event.event_id, name="Other Stage", display_order=1, external_id="os",
        color_hex="#ff4f9a",
    )
    db_session.add(other_stage)
    await db_session.flush()

    other_set = Set(
        event_id=other_event.event_id,
        stage_id=other_stage.stage_id,
        display_name="Other Set",
        day_label="SAT",
        starts_at=datetime(2026, 6, 20, 20, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 20, 21, 0, tzinfo=timezone.utc),
        external_id="other-set",
    )
    db_session.add(other_set)
    await db_session.flush()

    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(other_set.set_id), "state": "active", "state_clock_ms": _now_ms()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "set_not_in_group_event"


async def test_not_a_member_returns_403(
    client: AsyncClient,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    _, invite_code, _, _, set_id = pick_setup
    outsider_token, _ = await signup_and_get_token(client, "pick_outsider@example.com")
    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": _now_ms()},
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "not_a_member"


async def test_member_id_not_in_body_is_inferred(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, _, member_id, set_id = pick_setup
    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": _now_ms()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["member_id"] == str(member_id)


async def test_group_last_active_at_updated(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, group_id, _, set_id = pick_setup
    grp_before = (
        await db_session.execute(select(Group).where(Group.id == uuid.UUID(group_id)))
    ).scalar_one()
    before = grp_before.last_active_at

    r = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": _now_ms()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200

    await db_session.refresh(grp_before)
    assert grp_before.last_active_at >= before


async def test_concurrent_pick_higher_clock_wins(
    client: AsyncClient,
    db_session: AsyncSession,
    pick_setup: tuple[str, str, str, uuid.UUID, uuid.UUID],
) -> None:
    token, invite_code, _, member_id, set_id = pick_setup
    now = _now_ms()
    # Two sequential POSTs simulating concurrent requests; higher clock should win
    r1 = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "active", "state_clock_ms": now + 2000},
        headers={"Authorization": f"Bearer {token}"},
    )
    r2 = await client.post(
        f"/api/groups/{invite_code}/picks",
        json={"set_id": str(set_id), "state": "tombstoned", "state_clock_ms": now + 1000},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.json()["accepted"] is True
    assert r2.json()["accepted"] is False

    pick = (
        await db_session.execute(
            select(Pick).where(Pick.member_id == member_id, Pick.set_id == set_id)
        )
    ).scalar_one()
    assert pick.state_clock_ms == now + 2000
