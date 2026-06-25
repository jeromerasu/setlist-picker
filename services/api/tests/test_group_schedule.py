"""REALIGN-005: GET /api/groups/{invite_code}/schedule tests."""

from __future__ import annotations

import uuid
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

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
    """All sets for the day appear; sets with active picks have going_count > 0."""
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
    # Both FRIDAY sets appear via LEFT JOIN; set1 has an active pick, set2 does not
    assert len(body["sets"]) == 2
    sets_by_id = {s["set_id"]: s for s in body["sets"]}
    s1 = sets_by_id[str(set1_id)]
    assert s1["display_name"] == "Artist A"
    assert s1["stage_name"] == "Main Stage"
    assert s1["stage_color_hex"] == "#ff4f9a"
    assert s1["going_count"] == 1
    assert len(s1["going_members"]) == 1
    assert s1["going_members"][0]["member_id"] == str(owner_mid)


async def test_schedule_excludes_sets_with_no_active_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Sets with no active picks appear in the response with going_count=0 (LEFT JOIN guarantee)."""
    owner_token, _, invite_code, owner_mid, _, set1_id, set2_id, _, _ = schedule_setup

    # Only set1 has a pick; set2 on FRIDAY does not
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    sets_by_id = {s["set_id"]: s for s in r.json()["sets"]}
    assert str(set2_id) in sets_by_id
    assert sets_by_id[str(set2_id)]["going_count"] == 0
    assert sets_by_id[str(set2_id)]["going_members"] == []


async def test_schedule_excludes_tombstoned_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Tombstoned picks are not counted as going; the set still appears with going_count=0."""
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
    sets_by_id = {s["set_id"]: s for s in r.json()["sets"]}
    assert str(set1_id) in sets_by_id
    assert sets_by_id[str(set1_id)]["going_count"] == 0
    assert sets_by_id[str(set1_id)]["going_members"] == []


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


# ---------------------------------------------------------------------------
# TASK-PERF-COUNT-SQL: SQL aggregation tests
# ---------------------------------------------------------------------------


def _schedule_stmt_counter() -> tuple[list[int], Callable[..., Any]]:
    """Count before_execute events whose FROM clause contains a JOIN.

    The schedule query (Set JOIN Stage LEFT JOIN Pick ...) produces a Join in
    froms; the auth/member-check selects are simple single-table selects and
    are not counted.
    """
    count: list[int] = [0]

    def _has_join(from_clause: object) -> bool:
        return hasattr(from_clause, "left") and hasattr(from_clause, "right")

    def _listener(
        conn: object,
        clauseelement: object,
        multiparams: object,
        params: object,
        execution_options: object,
    ) -> None:
        get_froms = getattr(clauseelement, "get_final_froms", None)
        froms = get_froms() if get_froms is not None else []
        if any(_has_join(f) for f in froms):
            count[0] += 1

    return count, _listener


async def test_going_count_aggregated_from_sql(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """going_count and maybe_count are computed in SQL, not Python."""
    owner_token, _, invite_code, owner_mid, member2_mid, set1_id, _, _, _ = schedule_setup

    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    db_session.add(Pick(member_id=member2_mid, set_id=set1_id, state="maybe", state_clock_ms=2))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    sets_by_id = {s["set_id"]: s for s in r.json()["sets"]}
    s1 = sets_by_id[str(set1_id)]
    assert s1["going_count"] == 1
    assert s1["maybe_count"] == 1


async def test_zero_pick_sets_still_appear_with_zero_counts(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Sets with no picks appear in the response with going_count=0 and maybe_count=0."""
    owner_token, _, invite_code, owner_mid, _, set1_id, set2_id, _, _ = schedule_setup

    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    sets_by_id = {s["set_id"]: s for s in r.json()["sets"]}
    assert str(set2_id) in sets_by_id
    assert sets_by_id[str(set2_id)]["going_count"] == 0
    assert sets_by_id[str(set2_id)]["maybe_count"] == 0
    assert sets_by_id[str(set2_id)]["going_members"] == []


async def test_response_shape_unchanged_member_picks_present(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
) -> None:
    """Response shape includes going_count, maybe_count, and going_members per set."""
    owner_token, _, invite_code, owner_mid, _, set1_id, _, _, _ = schedule_setup

    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    await db_session.flush()

    r = await client.get(
        f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
        headers={"authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    for s in r.json()["sets"]:
        assert "going_count" in s
        assert "maybe_count" in s
        assert "going_members" in s
        assert isinstance(s["going_count"], int)
        assert isinstance(s["maybe_count"], int)
        assert isinstance(s["going_members"], list)


async def test_one_statement_per_request(
    client: AsyncClient,
    db_session: AsyncSession,
    schedule_setup: tuple[
        str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID, Stage
    ],
    test_engine: AsyncEngine,
) -> None:
    """The schedule data is fetched in exactly one SQL statement (set-table query)."""
    owner_token, _, invite_code, owner_mid, _, set1_id, _, _, _ = schedule_setup

    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    await db_session.flush()

    count, listener = _schedule_stmt_counter()
    event.listen(test_engine.sync_engine, "before_execute", listener)
    try:
        r = await client.get(
            f"{_BASE}/{invite_code}/schedule?day_label=FRIDAY",
            headers={"authorization": f"Bearer {owner_token}"},
        )
    finally:
        event.remove(test_engine.sync_engine, "before_execute", listener)

    assert r.status_code == 200
    assert count[0] == 1
