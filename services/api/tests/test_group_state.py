"""BE-009: GET /api/groups/{invite_code} — group state + conditional GET tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.db.models.event import Event
from tests.conftest import signup_and_get_token


@pytest.fixture
async def group_with_member(
    client: AsyncClient,
    test_event: Event,
) -> tuple[str, str, str, str, str]:
    """Returns (owner_token, member_token, invite_code, group_id, member_user_id)."""
    owner_token, _ = await signup_and_get_token(client, "state_owner")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "State Test Group"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert r.status_code == 201
    invite_code = r.json()["invite_code"]
    group_id = r.json()["group_id"]

    member_token, member_user_id = await signup_and_get_token(client, "state_member")
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
    token, _ = await signup_and_get_token(client, "state_notfound")
    r = await client.get("/api/groups/ZZZZZZZZ", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 404
    assert r.json()["detail"]["error_code"] == "group_not_found"


async def test_get_group_state_non_member_returns_403(
    client: AsyncClient,
    group_with_member: tuple[str, str, str, str, str],
) -> None:
    _, _, invite_code, _, _ = group_with_member
    outsider_token, _ = await signup_and_get_token(client, "outsider_state")
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
