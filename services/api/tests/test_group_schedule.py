"""REALIGN-005: GET /api/groups/{invite_code}/schedule tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from app.db.models.pick import Pick
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from tests.conftest import signup_and_get_token

pytestmark = pytest.mark.anyio

_BASE = "/api/groups"


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------


@pytest.fixture
async def schedule_setup(
    client: AsyncClient,
    db_session: AsyncSession,
    test_event: Event,
) -> tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage]:
    """
    Two members in one group with two stages and three sets across two days.

    Returns:
      owner_token, member_token, invite_code,
      owner_member_id, member2_member_id,
      set1_id (FRIDAY, stage1), set2_id (FRIDAY, stage2), set3_id (SATURDAY, stage1),
      stage1
    """
    owner_token, _ = await signup_and_get_token(client, "sched_owner@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Sched Group"},
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    owner_member_id = uuid.UUID(r.json()["member_id"])

    member_token, _ = await signup_and_get_token(client, "sched_member@example.com")
    rj = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"authorization": f"Bearer {member_token}"},
    )
    assert rj.status_code == 201
    member2_member_id = uuid.UUID(rj.json()["member"]["member_id"])

    stage1 = Stage(
        event_id=test_event.event_id,
        name="Main Stage",
        display_order=10,
        external_id="main-stage-sched",
        color_hex="#ff4f9a",
    )
    stage2 = Stage(
        event_id=test_event.event_id,
        name="Second Stage",
        display_order=20,
        external_id="second-stage-sched",
        color_hex="#36c6ff",
    )
    db_session.add_all([stage1, stage2])
    await db_session.flush()

    set1 = Set(
        event_id=test_event.event_id,
        stage_id=stage1.stage_id,
        display_name="Artist A",
        day_label="FRIDAY",
        starts_at=datetime(2026, 6, 20, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 20, 15, 0, tzinfo=timezone.utc),
        external_id="sched-set1",
    )
    set2 = Set(
        event_id=test_event.event_id,
        stage_id=stage2.stage_id,
        display_name="Artist B",
        day_label="FRIDAY",
        starts_at=datetime(2026, 6, 20, 16, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 20, 17, 0, tzinfo=timezone.utc),
        external_id="sched-set2",
    )
    set3 = Set(
        event_id=test_event.event_id,
        stage_id=stage1.stage_id,
        display_name="Artist C",
        day_label="SATURDAY",
        starts_at=datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 21, 13, 0, tzinfo=timezone.utc),
        external_id="sched-set3",
    )
    db_session.add_all([set1, set2, set3])
    await db_session.flush()

    return (
        owner_token,
        member_token,
        invite_code,
        owner_member_id,
        member2_member_id,
        set1.set_id,
        set2.set_id,
        set3.set_id,
        stage1,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


async def test_schedule_returns_sets_with_active_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Returns only sets where at least one group member has an active pick."""
    owner_token, _, invite_code, owner_mid, _, set1_id, set2_id, _, _ = schedule_setup

    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["day_label"] == "FRIDAY"
    assert len(body["sets"]) == 1
    assert body["sets"][0]["set_id"] == str(set1_id)
    assert body["sets"][0]["display_name"] == "Artist A"
    assert body["sets"][0]["stage_name"] == "Main Stage"
    assert body["sets"][0]["stage_color_hex"] == "#ff4f9a"
    assert len(body["sets"][0]["going_members"]) == 1
    assert body["sets"][0]["going_members"][0]["member_id"] == str(owner_mid)


async def test_schedule_excludes_sets_with_no_active_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Sets with no active picks are absent from the response."""
    owner_token, _, invite_code, owner_mid, _, set1_id, set2_id, _, _ = schedule_setup

    # Only set1 has a pick; set2 on FRIDAY does not
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    set_ids = [s["set_id"] for s in r.json()["sets"]]
    assert str(set2_id) not in set_ids


async def test_schedule_excludes_tombstoned_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Tombstoned picks do not count as going."""
    owner_token, _, invite_code, owner_mid, _, set1_id, set2_id, _, _ = schedule_setup

    db_session.add(
        Pick(member_id=owner_mid, set_id=set1_id, state="tombstoned", state_clock_ms=5)
    )
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    assert r.json()["sets"] == []


async def test_schedule_returns_403_for_non_member(
    client: AsyncClient,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Caller who is not in the group gets 403."""
    _, _, invite_code = schedule_setup[:3]
    outsider_token, _ = await signup_and_get_token(client, "sched_outsider@example.com")

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {outsider_token}"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "not_a_member"


async def test_schedule_returns_empty_sets_for_day_with_no_picks(
    client: AsyncClient,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """No picks for the requested day_label → 200 with empty sets list."""
    owner_token, _, invite_code = schedule_setup[:3]

    # No picks exist at all — requesting any day should return empty
    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=SUNDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    assert r.json()["sets"] == []


async def test_schedule_going_members_sorted_by_joined_at(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """going_members are ordered by joined_at ascending (first joiner first)."""
    owner_token, _, invite_code, owner_mid, member2_mid, set1_id, _, _, _ = schedule_setup

    # Both members going to set1
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    db_session.add(Pick(member_id=member2_mid, set_id=set1_id, state="active", state_clock_ms=2))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    going = r.json()["sets"][0]["going_members"]
    assert len(going) == 2
    # Owner joined first (created group), member2 joined after
    assert going[0]["member_id"] == str(owner_mid)
    assert going[1]["member_id"] == str(member2_mid)


async def test_schedule_sets_sorted_by_starts_at(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """sets are sorted ascending by starts_at."""
    owner_token, _, invite_code, owner_mid, _, set1_id, set2_id, _, _ = schedule_setup

    # set2 starts later than set1
    db_session.add(Pick(member_id=owner_mid, set_id=set2_id, state="active", state_clock_ms=1))
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=2))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    sets = r.json()["sets"]
    assert len(sets) == 2
    assert sets[0]["set_id"] == str(set1_id)   # starts 14:00
    assert sets[1]["set_id"] == str(set2_id)   # starts 16:00


async def test_schedule_day_label_filters_correctly(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Only sets matching the requested day_label are returned."""
    owner_token, _, invite_code, owner_mid, _, set1_id, _, set3_id, _ = schedule_setup

    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    db_session.add(Pick(member_id=owner_mid, set_id=set3_id, state="active", state_clock_ms=2))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=SATURDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    sets = r.json()["sets"]
    assert len(sets) == 1
    assert sets[0]["set_id"] == str(set3_id)
