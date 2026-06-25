"""TASK-SETLIST-PERF-BATCH-UPSERT: single-statement pick sync + LWW correctness tests."""

from __future__ import annotations

import time
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


def _now_ms() -> int:
    return int(time.time() * 1000)


@pytest.fixture
async def batch_setup(
    client: AsyncClient,
    db_session: AsyncSession,
    test_event: Event,
) -> tuple[str, str, uuid.UUID, list[uuid.UUID]]:
    """Returns (token, invite_code, member_id, set_ids[0..52])."""
    token, _ = await signup_and_get_token(client, "batchsync@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Batch Sync Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    member_id = uuid.UUID(r.json()["member_id"])

    stage = Stage(
        event_id=test_event.event_id,
        name="Batch Stage",
        display_order=5,
        external_id="batch-stage",
        color_hex="#00ccff",
    )
    db_session.add(stage)
    await db_session.flush()

    set_ids: list[uuid.UUID] = []
    for i in range(53):
        s = Set(
            event_id=test_event.event_id,
            stage_id=stage.stage_id,
            display_name=f"Batch Set {i}",
            day_label="SUN",
            starts_at=datetime(2026, 6, 21, 10 + (i % 8), 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 21, 11 + (i % 8), 0, tzinfo=timezone.utc),
            external_id=f"batch-set-{i}",
        )
        db_session.add(s)
        await db_session.flush()
        set_ids.append(s.set_id)

    return token, invite_code, member_id, set_ids


def _pick_stmt_counter() -> tuple[list[int], Callable[..., Any]]:
    """Returns (count_list, listener_fn). count_list[0] increments per pick-table DML."""
    count: list[int] = [0]

    def _listener(conn: object, clauseelement: object, multiparams: object,
                  params: object, execution_options: object) -> None:
        tbl = getattr(clauseelement, "table", None)
        if tbl is not None and getattr(tbl, "name", None) == "pick":
            count[0] += 1

    return count, _listener


async def test_batch_of_50_executes_one_statement(
    client: AsyncClient,
    db_session: AsyncSession,
    batch_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
    test_engine: AsyncEngine,
) -> None:
    token, invite_code, _, set_ids = batch_setup
    now = _now_ms()
    toggles = [
        {"set_id": str(set_ids[i]), "state": "active", "state_clock_ms": now + i}
        for i in range(50)
    ]

    count, listener = _pick_stmt_counter()
    event.listen(test_engine.sync_engine, "before_execute", listener)
    try:
        r = await client.post(
            f"/api/groups/{invite_code}/picks/sync",
            json={"toggles": toggles},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        event.remove(test_engine.sync_engine, "before_execute", listener)

    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 50
    assert all(res["accepted"] for res in results)
    assert count[0] == 1


async def test_all_stale_clocks_no_writes(
    client: AsyncClient,
    db_session: AsyncSession,
    batch_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
    test_engine: AsyncEngine,
) -> None:
    token, invite_code, member_id, set_ids = batch_setup
    # int(9e12) ≈ year 2255 in unix-ms — guaranteed higher than any current timestamp
    HIGH_CLOCK = int(9e12)
    for sid in set_ids[:3]:
        db_session.add(
            Pick(member_id=member_id, set_id=sid, state="active", state_clock_ms=HIGH_CLOCK)
        )
    await db_session.flush()

    now = _now_ms()
    toggles = [
        {"set_id": str(set_ids[i]), "state": "tombstoned", "state_clock_ms": now + i}
        for i in range(3)
    ]

    count, listener = _pick_stmt_counter()
    event.listen(test_engine.sync_engine, "before_execute", listener)
    try:
        r = await client.post(
            f"/api/groups/{invite_code}/picks/sync",
            json={"toggles": toggles},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        event.remove(test_engine.sync_engine, "before_execute", listener)

    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    assert not any(res["accepted"] for res in results)
    # Verify DB rows still have the original high clock (no writes occurred)
    from sqlalchemy import select as sa_select
    for sid in set_ids[:3]:
        row_result = await db_session.execute(
            sa_select(Pick)
            .where(Pick.member_id == member_id, Pick.set_id == sid)
            .execution_options(populate_existing=True)
        )
        row = row_result.scalar_one()
        assert row.state_clock_ms == HIGH_CLOCK
    assert count[0] == 1


async def test_mixed_fresh_and_stale_writes_only_fresh(
    client: AsyncClient,
    db_session: AsyncSession,
    batch_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
    test_engine: AsyncEngine,
) -> None:
    token, invite_code, member_id, set_ids = batch_setup
    HIGH_CLOCK = int(9e12)
    for sid in set_ids[:2]:
        db_session.add(
            Pick(member_id=member_id, set_id=sid, state="active", state_clock_ms=HIGH_CLOCK)
        )
    await db_session.flush()

    now = _now_ms()
    toggles = [
        {"set_id": str(set_ids[0]), "state": "tombstoned", "state_clock_ms": 100},  # stale
        {"set_id": str(set_ids[1]), "state": "tombstoned", "state_clock_ms": 100},  # stale
        {"set_id": str(set_ids[2]), "state": "active", "state_clock_ms": now},       # fresh
    ]

    count, listener = _pick_stmt_counter()
    event.listen(test_engine.sync_engine, "before_execute", listener)
    try:
        r = await client.post(
            f"/api/groups/{invite_code}/picks/sync",
            json={"toggles": toggles},
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        event.remove(test_engine.sync_engine, "before_execute", listener)

    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    assert results[0]["accepted"] is False  # stale
    assert results[1]["accepted"] is False  # stale
    assert results[2]["accepted"] is True   # fresh
    assert count[0] == 1


async def test_single_pick_array_still_works(
    client: AsyncClient,
    db_session: AsyncSession,
    batch_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
) -> None:
    token, invite_code, _, set_ids = batch_setup
    now = _now_ms()
    r = await client.post(
        f"/api/groups/{invite_code}/picks/sync",
        json={"toggles": [{"set_id": str(set_ids[0]), "state": "active", "state_clock_ms": now}]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 1
    assert results[0]["accepted"] is True
    assert results[0]["state"] == "active"


async def test_response_shape_unchanged(
    client: AsyncClient,
    db_session: AsyncSession,
    batch_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
) -> None:
    token, invite_code, _, set_ids = batch_setup
    now = _now_ms()
    toggles = [
        {"set_id": str(set_ids[i]), "state": "active", "state_clock_ms": now + i}
        for i in range(3)
    ]
    r = await client.post(
        f"/api/groups/{invite_code}/picks/sync",
        json={"toggles": toggles},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert "results" in body
    for result in body["results"]:
        assert "member_id" in result
        assert "set_id" in result
        assert "state" in result
        assert "state_clock_ms" in result
        assert "accepted" in result
