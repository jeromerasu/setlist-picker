"""BE-006: POST /api/groups — create group tests."""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from unittest.mock import patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.invite_code import CROCKFORD_ALPHABET
from app.db.models.event import Event
from app.db.models.group import Group
from app.db.models.group_activity import GroupActivity
from app.db.models.member import Member
from tests.conftest import signup_and_get_token


@pytest.fixture
async def event_and_token(
    client: AsyncClient,
    test_event: Event,
) -> tuple[str, str, str]:
    """Returns (access_token, user_id, str(event_id))."""
    token, user_id = await signup_and_get_token(client, "groupcreator@example.com")
    return token, user_id, str(test_event.event_id)


async def test_create_group_unauthenticated_returns_401(
    client: AsyncClient,
    test_event: Event,
) -> None:
    r = await client.post("/api/groups", json={"event_id": str(test_event.event_id)})
    assert r.status_code == 401


async def test_create_group_event_not_found_returns_404(client: AsyncClient) -> None:
    token, _ = await signup_and_get_token(client, "notfound_user@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(uuid.uuid4())},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "event_not_found"


async def test_create_group_minimal_payload_returns_201(
    client: AsyncClient,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token
    r = await client.post(
        "/api/groups",
        json={"event_id": event_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Friends 🎵"
    assert body["event_id"] == event_id


async def test_create_group_with_name_returns_201(
    client: AsyncClient,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token
    r = await client.post(
        "/api/groups",
        json={"event_id": event_id, "name": "Ravers"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Ravers"


async def test_create_group_uses_provided_name_after_strip(
    client: AsyncClient,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token
    r = await client.post(
        "/api/groups",
        json={"event_id": event_id, "name": "  ravers "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "ravers"


async def test_create_group_blank_name_returns_422(
    client: AsyncClient,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token
    r = await client.post(
        "/api/groups",
        json={"event_id": event_id, "name": "   "},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_create_group_response_includes_member_id(
    client: AsyncClient,
    db_session: AsyncSession,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token
    r = await client.post(
        "/api/groups",
        json={"event_id": event_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    member_id = uuid.UUID(body["member_id"])
    result = await db_session.execute(select(Member).where(Member.id == member_id))
    assert result.scalar_one_or_none() is not None


async def test_create_group_invite_code_is_crockford(
    client: AsyncClient,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token
    r = await client.post(
        "/api/groups",
        json={"event_id": event_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    code = r.json()["invite_code"]
    assert len(code) == 8
    assert all(c in CROCKFORD_ALPHABET for c in code)


async def test_create_group_logs_group_created_activity(
    client: AsyncClient,
    db_session: AsyncSession,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token
    r = await client.post(
        "/api/groups",
        json={"event_id": event_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    group_id = uuid.UUID(r.json()["group_id"])
    result = await db_session.execute(
        select(GroupActivity).where(
            GroupActivity.group_id == group_id,
            GroupActivity.kind == "group_created",
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert "group_name" in row.payload
    assert "event_id" in row.payload
    assert "event_name" in row.payload


async def test_create_group_collision_retries_and_succeeds(
    client: AsyncClient,
    db_session: AsyncSession,
    event_and_token: tuple[str, str, str],
) -> None:
    token, user_id, event_id = event_and_token

    # Pre-insert a group with code "00000000" to force one collision
    dup = Group(
        invite_code="00000000",
        event_id=uuid.UUID(event_id),
        created_by_user_id=uuid.UUID(user_id),
        name="Dup",
    )
    db_session.add(dup)
    await db_session.flush()

    calls: Iterator[str] = iter(["00000000", "ZZZZZZZZ"])
    with patch("app.services.group_service.generate_invite_code", side_effect=calls):
        r = await client.post(
            "/api/groups",
            json={"event_id": event_id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 201
    assert r.json()["invite_code"] == "ZZZZZZZZ"


async def test_create_group_collision_max_retries_returns_500(
    client: AsyncClient,
    db_session: AsyncSession,
    event_and_token: tuple[str, str, str],
) -> None:
    token, user_id, event_id = event_and_token

    # Pre-insert group with "00000000" so every attempt collides
    dup = Group(
        invite_code="00000000",
        event_id=uuid.UUID(event_id),
        created_by_user_id=uuid.UUID(user_id),
        name="Dup",
    )
    db_session.add(dup)
    await db_session.flush()

    with patch("app.services.group_service.generate_invite_code", return_value="00000000"):
        r = await client.post(
            "/api/groups",
            json={"event_id": event_id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 500
    assert r.json()["detail"]["error_code"] == "invite_code_collision_unrecoverable"


async def test_create_group_atomic_on_member_failure(
    client: AsyncClient,
    db_session: AsyncSession,
    event_and_token: tuple[str, str, str],
) -> None:
    token, _, event_id = event_and_token

    # Patch Member constructor to raise after Group is inserted
    with patch("app.services.group_service.Member", side_effect=RuntimeError("forced")):
        r = await client.post(
            "/api/groups",
            json={"event_id": event_id},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert r.status_code == 500
    # SAVEPOINT was rolled back — no orphaned Group rows
    result = await db_session.execute(select(Group))
    assert result.scalars().all() == []
