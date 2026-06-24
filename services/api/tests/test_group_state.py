"""BE-009/BE-014: GET /api/groups/{invite_code} — group state + picks payload tests."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from app.db.models.member import Member
from app.db.models.pick import Pick
from app.db.models.set_ import Set
from app.db.models.stage import Stage
from tests.conftest import signup_and_get_token


@pytest.fixture
async def group_with_member(
    client: AsyncClient,
    test_event: Event,
) -> tuple[str, str, str, str, str]:
    """Returns (owner_token, member_token, invite_code, group_id, member_user_id)."""
    owner_token, _ = await signup_and_get_token(client, "state_owner@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "State Test Group"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    group_id = r.json()["group_id"]

    member_token, member_user_id = await signup_and_get_token(client, "state_member@example.com")
    await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    return owner_token, member_token, invite_code, group_id, member_user_id


async def test_get_group_state_unauthenticated_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/groups/ABCD1234")
    assert r.status_code == 401


async def test_get_group_state_not_found_returns_404(client: AsyncClient) -> None:
    token, _ = await signup_and_get_token(client, "state_notfound@example.com")
    r = await client.get("/api/groups/ZZZZZZZZ", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "group_not_found"


async def test_get_group_state_non_member_returns_403(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, _, invite_code, _, _ = group_with_member
    outsider_token, _ = await signup_and_get_token(client, "outsider_state@example.com")
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {outsider_token}"},
    )
    assert r.status_code == 403
    assert r.json()["detail"]["error_code"] == "not_a_member"


async def test_get_group_state_returns_200_for_member(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, _, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200


async def test_get_group_state_response_shape(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, group_id, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["group_id"] == group_id
    assert body["invite_code"] == invite_code
    assert "event" in body
    assert "members" in body
    assert "picks" in body
    assert "last_active_at" in body
    assert "archived_at" in body


async def test_get_group_state_includes_all_members(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, _, member_user_id = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200
    user_ids = {m["user_id"] for m in r.json()["members"]}
    assert member_user_id in user_ids
    assert len(r.json()["members"]) == 2  # owner + member


async def test_get_group_state_event_summary_shape(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
    test_event: Event,
) -> None:
    _, member_token, invite_code, _, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200
    event = r.json()["event"]
    assert event["event_id"] == str(test_event.event_id)
    assert event["name"] == test_event.name
    for field in ("start_date", "end_date", "timezone"):
        assert field in event


async def test_get_group_state_sets_last_modified_header(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, _, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200
    assert "last-modified" in r.headers


async def test_get_group_state_304_when_not_modified(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, _, _ = group_with_member
    headers = {"Authorization": f"Bearer {member_token}"}

    # First request to get Last-Modified
    r1 = await client.get(f"/api/groups/{invite_code}", headers=headers)
    assert r1.status_code == 200
    last_modified = r1.headers["last-modified"]

    # Second request with If-Modified-Since
    r2 = await client.get(
        f"/api/groups/{invite_code}",
        headers={**headers, "if-modified-since": last_modified},
    )
    assert r2.status_code == 304


async def test_get_group_state_200_when_modified_since_older(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, _, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={
            "Authorization": f"Bearer {member_token}",
            "if-modified-since": "Tue, 01 Jan 2020 00:00:00 GMT",
        },
    )
    assert r.status_code == 200


async def test_get_group_state_normalize_invite_code(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, _, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code.lower()}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200


async def test_get_group_state_picks_empty_initially(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, member_token, invite_code, _, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200
    assert r.json()["picks"] == []


async def test_get_group_state_malformed_if_modified_since_ignored(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    """A malformed If-Modified-Since header is silently ignored — returns 200."""
    _, member_token, invite_code, _, _ = group_with_member
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={
            "Authorization": f"Bearer {member_token}",
            "if-modified-since": "garbage-date",
        },
    )
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# BE-014 — picks payload denormalization tests
# ---------------------------------------------------------------------------


@pytest.fixture
async def picks_setup(
    client: AsyncClient,
    db_session: AsyncSession,
    test_event: Event,
) -> tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    """Create group + 2 members + stage + 2 sets.

    Returns (owner_token, member_token, invite_code,
             owner_member_id, member2_member_id, set1_id, set2_id).
    """
    owner_token, _ = await signup_and_get_token(client, "picks_owner@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Picks Group"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    owner_member_id = uuid.UUID(r.json()["member_id"])

    member_token, _ = await signup_and_get_token(client, "picks_member@example.com")
    jr = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert jr.status_code == 201
    member2_member_id = uuid.UUID(jr.json()["member"]["member_id"])

    stage = Stage(
        event_id=test_event.event_id,
        name="Test Stage",
        display_order=1,
        external_id="test-stage",
        color_hex="#ff4f9a",
    )
    db_session.add(stage)
    await db_session.flush()

    set1 = Set(
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        display_name="Set One",
        day_label="FRIDAY",
        starts_at=datetime(2026, 6, 20, 14, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 20, 15, 0, tzinfo=timezone.utc),
        external_id="set-one",
    )
    set2 = Set(
        event_id=test_event.event_id,
        stage_id=stage.stage_id,
        display_name="Set Two",
        day_label="FRIDAY",
        starts_at=datetime(2026, 6, 20, 16, 0, tzinfo=timezone.utc),
        ends_at=datetime(2026, 6, 20, 17, 0, tzinfo=timezone.utc),
        external_id="set-two",
    )
    db_session.add(set1)
    db_session.add(set2)
    await db_session.flush()

    return (
        owner_token,
        member_token,
        invite_code,
        owner_member_id,
        member2_member_id,
        set1.set_id,
        set2.set_id,
    )


async def test_get_group_state_includes_active_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    picks_setup: tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    owner_token, _, invite_code, owner_mid, _, set1_id, set2_id = picks_setup
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1000))
    db_session.add(Pick(member_id=owner_mid, set_id=set2_id, state="active", state_clock_ms=2000))
    await db_session.flush()

    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    picks = r.json()["picks"]
    assert len(picks) == 2
    assert all(p["state"] == "active" for p in picks)


async def test_get_group_state_includes_tombstoned_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    picks_setup: tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    owner_token, _, invite_code, owner_mid, _, set1_id, _ = picks_setup
    db_session.add(
        Pick(member_id=owner_mid, set_id=set1_id, state="tombstoned", state_clock_ms=999)
    )
    await db_session.flush()

    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    picks = r.json()["picks"]
    assert len(picks) == 1
    assert picks[0]["state"] == "tombstoned"


async def test_get_group_state_picks_sorted_by_member_then_set(
    client: AsyncClient,
    db_session: AsyncSession,
    picks_setup: tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    owner_token, _, invite_code, owner_mid, m2_mid, set1_id, set2_id = picks_setup
    db_session.add(Pick(member_id=owner_mid, set_id=set2_id, state="active", state_clock_ms=1))
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=2))
    db_session.add(Pick(member_id=m2_mid, set_id=set1_id, state="active", state_clock_ms=3))
    await db_session.flush()

    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 200
    picks = r.json()["picks"]
    assert len(picks) == 3
    keys = [(p["member_id"], p["set_id"]) for p in picks]
    assert keys == sorted(keys)


async def test_get_group_state_picks_include_all_members_not_just_caller(
    client: AsyncClient,
    db_session: AsyncSession,
    picks_setup: tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    _, member_token, invite_code, owner_mid, m2_mid, set1_id, set2_id = picks_setup
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=1))
    db_session.add(Pick(member_id=owner_mid, set_id=set2_id, state="active", state_clock_ms=2))
    db_session.add(Pick(member_id=m2_mid, set_id=set1_id, state="active", state_clock_ms=3))
    await db_session.flush()

    # Caller is member_token (m2_mid) — they should see all 3 picks including owner's
    r = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {member_token}"},
    )
    assert r.status_code == 200
    assert len(r.json()["picks"]) == 3


async def test_get_group_state_last_modified_reflects_picks(
    client: AsyncClient,
    db_session: AsyncSession,
    picks_setup: tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    from sqlalchemy import select

    from app.db.models.group import Group

    owner_token, _, invite_code, owner_mid, _, set1_id, _ = picks_setup

    r1 = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r1.status_code == 200
    lm1 = r1.headers["last-modified"]

    # Add a pick and bump group.last_active_at (as BE-015 will do)
    db_session.add(Pick(member_id=owner_mid, set_id=set1_id, state="active", state_clock_ms=500))
    grp_result = await db_session.execute(select(Group).where(Group.invite_code == invite_code))
    grp = grp_result.scalar_one()
    grp.last_active_at = datetime.now(timezone.utc) + timedelta(seconds=5)
    await db_session.flush()

    r2 = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r2.status_code == 200
    lm2 = r2.headers["last-modified"]
    assert lm2 != lm1


async def test_get_group_state_picks_excluded_when_member_leaves(
    client: AsyncClient,
    db_session: AsyncSession,
    picks_setup: tuple[str, str, str, uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    owner_token, _, invite_code, owner_mid, m2_mid, set1_id, _ = picks_setup
    db_session.add(Pick(member_id=m2_mid, set_id=set1_id, state="active", state_clock_ms=999))
    await db_session.flush()

    # Verify pick is visible
    r1 = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert len(r1.json()["picks"]) == 1

    # Delete member → picks cascade
    await db_session.execute(delete(Member).where(Member.id == m2_mid))
    await db_session.flush()

    r2 = await client.get(
        f"/api/groups/{invite_code}",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["picks"] == []
