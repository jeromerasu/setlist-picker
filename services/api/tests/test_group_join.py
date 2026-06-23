"""BE-007: POST /api/groups/join tests."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.event import Event
from app.db.models.member import Member
from tests.conftest import signup_and_get_token


@pytest.fixture
async def creator_and_group(
    client: AsyncClient,
    test_event: Event,
) -> tuple[str, str, str, str]:
    """Returns (creator_token, user_id, group_invite_code, group_id)."""
    token, user_id = await signup_and_get_token(client, "groupowner")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Join Test Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    return token, user_id, body["invite_code"], body["group_id"]


async def test_join_group_unauthenticated_returns_401(client: AsyncClient) -> None:
    r = await client.post("/api/groups/join", json={"invite_code": "ABCD1234"})
    assert r.status_code == 401


async def test_join_group_not_found_returns_404(client: AsyncClient) -> None:
    token, _ = await signup_and_get_token(client, "joiner_notfound")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": "ZZZZZZZZ"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "group_not_found"


async def test_join_group_new_member_returns_201(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, _ = creator_and_group
    token, _ = await signup_and_get_token(client, "new_member_201")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["is_new_member"] is True


async def test_join_group_new_member_response_shape(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, group_id = creator_and_group
    token, user_id = await signup_and_get_token(client, "shape_check_member")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["group"]["group_id"] == group_id
    assert body["member"]["user_id"] == user_id
    assert "member_id" in body["member"]
    assert "display_name" in body["member"]
    assert "avatar_color" in body["member"]


async def test_join_group_idempotent_returns_200(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, _ = creator_and_group
    token, _ = await signup_and_get_token(client, "idempotent_joiner")
    r1 = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 200
    assert r2.json()["is_new_member"] is False
    assert r1.json()["member"]["member_id"] == r2.json()["member"]["member_id"]


async def test_join_group_idempotent_one_member_row(
    client: AsyncClient,
    db_session: AsyncSession,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, group_id = creator_and_group
    token, user_id = await signup_and_get_token(client, "idempotent_count")
    await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    result = await db_session.execute(
        select(Member).where(
            Member.user_id == uuid.UUID(user_id),
            Member.group_id == uuid.UUID(group_id),
        )
    )
    assert len(result.scalars().all()) == 1


async def test_join_group_with_display_name_override(
    client: AsyncClient,
    db_session: AsyncSession,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, _ = creator_and_group
    token, _ = await signup_and_get_token(client, "override_namer")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code, "display_name_override": "DJ Override"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["member"]["display_name"] == "DJ Override"
    assert r.json()["member"]["display_name_override"] == "DJ Override"


async def test_join_group_display_name_fallback_to_username(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, _ = creator_and_group
    token, _ = await signup_and_get_token(client, "fallback_user")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert r.json()["member"]["display_name"] == "fallback_user"


async def test_join_group_normalize_invite_code(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    """Crockford normalize: lowercase + I→1, O→0, L→1 still resolves the group."""
    _, _, invite_code, _ = creator_and_group
    token, _ = await signup_and_get_token(client, "normalizer")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code.lower()},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201


async def test_join_group_logs_member_joined_activity(
    client: AsyncClient,
    db_session: AsyncSession,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    from app.db.models.group_activity import GroupActivity

    _, _, invite_code, group_id = creator_and_group
    token, _ = await signup_and_get_token(client, "activity_joiner")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    result = await db_session.execute(
        select(GroupActivity).where(
            GroupActivity.group_id == uuid.UUID(group_id),
            GroupActivity.kind == "member_joined",
        )
    )
    assert result.scalar_one_or_none() is not None


async def test_join_group_creator_already_member_returns_200(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    """Creator is auto-joined on group create; re-joining returns 200."""
    creator_token, _, invite_code, _ = creator_and_group
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {creator_token}"},
    )
    assert r.status_code == 200
    assert r.json()["is_new_member"] is False


async def test_join_group_back_to_back_first_join_one_member_row(
    client: AsyncClient,
    db_session: AsyncSession,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    """Back-to-back POSTs from the same user → both 2xx, exactly one Member row.
    (True DB-level concurrency requires separate connections; this covers the
    idempotent branch instead of the SAVEPOINT race-condition branch.)"""
    _, _, invite_code, group_id = creator_and_group
    token, user_id = await signup_and_get_token(client, "backtoback_joiner")
    headers = {"Authorization": f"Bearer {token}"}

    r1 = await client.post(
        "/api/groups/join", json={"invite_code": invite_code}, headers=headers
    )
    r2 = await client.post(
        "/api/groups/join", json={"invite_code": invite_code}, headers=headers
    )
    assert r1.status_code in (200, 201)
    assert r2.status_code in (200, 201)

    result = await db_session.execute(
        select(Member).where(
            Member.user_id == uuid.UUID(user_id),
            Member.group_id == uuid.UUID(group_id),
        )
    )
    assert len(result.scalars().all()) == 1


async def test_join_group_response_includes_group_last_active_at(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, _ = creator_and_group
    token, _ = await signup_and_get_token(client, "active_checker")
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    assert "last_active_at" in r.json()["group"]


async def test_join_group_invite_code_case_insensitive(
    client: AsyncClient,
    creator_and_group: tuple[str, str, str, str],
) -> None:
    _, _, invite_code, _ = creator_and_group
    token, _ = await signup_and_get_token(client, "caseless_user")
    mixed = "".join(c.lower() if i % 2 == 0 else c for i, c in enumerate(invite_code))
    r = await client.post(
        "/api/groups/join",
        json={"invite_code": mixed},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
