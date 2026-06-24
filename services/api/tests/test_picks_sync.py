"""BE-015: POST /api/groups/{invite_code}/picks/sync — batch LWW tests."""

from __future__ import annotations

import time
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


@pytest.fixture
async def sync_setup(
    client: AsyncClient,
    db_session: AsyncSession,
    test_event: Event,
) -> tuple[str, str, uuid.UUID, list[uuid.UUID]]:
    """Returns (token, invite_code, member_id, [set_id_1, set_id_2, set_id_3])."""
    token, _ = await signup_and_get_token(client, "sync_user@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Sync Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    member_id = uuid.UUID(r.json()["member_id"])

    stage = Stage(
        event_id=test_event.event_id,
        name="Sync Stage",
        display_order=1,
        external_id="sync-stage",
        color_hex="#ff4f9a",
    )
    db_session.add(stage)
    await db_session.flush()

    set_ids = []
    for i in range(3):
        s = Set(
            event_id=test_event.event_id,
            stage_id=stage.stage_id,
            display_name=f"Sync Set {i}",
            day_label="SAT",
            starts_at=datetime(2026, 6, 20, 14 + i, 0, tzinfo=timezone.utc),
            ends_at=datetime(2026, 6, 20, 15 + i, 0, tzinfo=timezone.utc),
            external_id=f"sync-set-{i}",
        )
        db_session.add(s)
        await db_session.flush()
        set_ids.append(s.set_id)

    return token, invite_code, member_id, set_ids


def _now_ms() -> int:
    return int(time.time() * 1000)


async def test_sync_processes_all_toggles_in_one_transaction(
    client: AsyncClient,
    db_session: AsyncSession,
    sync_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
) -> None:
    token, invite_code, _, set_ids = sync_setup
    now = _now_ms()
    toggles = [
        {"set_id": str(s), "state": "active", "state_clock_ms": now + i}
        for i, s in enumerate(set_ids)
    ]
    r = await client.post(
        f"/api/groups/{invite_code}/picks/sync",
        json={"toggles": toggles},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 3
    assert all(res["accepted"] for res in results)


async def test_sync_mixed_lww_results_returns_200_with_per_row_status(
    client: AsyncClient,
    db_session: AsyncSession,
    sync_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
) -> None:
    token, invite_code, member_id, set_ids = sync_setup
    # Pre-seed two rows with high clocks
    for s in set_ids[:2]:
        db_session.add(Pick(member_id=member_id, set_id=s, state="active", state_clock_ms=9999))
    await db_session.flush()

    now = _now_ms()
    toggles = [
        {"set_id": str(set_ids[0]), "state": "tombstoned", "state_clock_ms": 100},
        {"set_id": str(set_ids[1]), "state": "tombstoned", "state_clock_ms": 100},
        {"set_id": str(set_ids[2]), "state": "active", "state_clock_ms": now},
        {"set_id": str(set_ids[2]), "state": "tombstoned", "state_clock_ms": now + 1},
    ]
    r = await client.post(
        f"/api/groups/{invite_code}/picks/sync",
        json={"toggles": toggles},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 4
    accepted = [res["accepted"] for res in results]
    assert accepted.count(True) == 2
    assert accepted.count(False) == 2


async def test_sync_invalid_set_id_skips_row_logs_warning(
    client: AsyncClient,
    db_session: AsyncSession,
    sync_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
) -> None:
    token, invite_code, _, set_ids = sync_setup
    now = _now_ms()
    toggles = [
        {"set_id": str(uuid.uuid4()), "state": "active", "state_clock_ms": now},
        {"set_id": str(set_ids[0]), "state": "active", "state_clock_ms": now + 1},
    ]
    r = await client.post(
        f"/api/groups/{invite_code}/picks/sync",
        json={"toggles": toggles},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) == 2
    # First row (bad set_id) → rejected; second row → accepted
    assert results[0]["accepted"] is False
    assert results[1]["accepted"] is True


async def test_sync_empty_batch_returns_422(
    client: AsyncClient,
    sync_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
) -> None:
    token, invite_code, _, _ = sync_setup
    r = await client.post(
        f"/api/groups/{invite_code}/picks/sync",
        json={"toggles": []},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_sync_batch_too_large_returns_422(
    client: AsyncClient,
    sync_setup: tuple[str, str, uuid.UUID, list[uuid.UUID]],
) -> None:
    token, invite_code, _, set_ids = sync_setup
    toggles = [
        {"set_id": str(set_ids[0]), "state": "active", "state_clock_ms": i} for i in range(501)
    ]
    r = await client.post(
        f"/api/groups/{invite_code}/picks/sync",
        json={"toggles": toggles},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422
