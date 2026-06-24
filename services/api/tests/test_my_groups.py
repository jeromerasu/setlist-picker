"""BE-008: GET /api/users/me/groups tests."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.db.models.event import Event
from tests.conftest import signup_and_get_token


@pytest.fixture
async def multi_group_setup(
    client: AsyncClient,
    test_event: Event,
) -> tuple[str, list[str]]:
    """Creates a user who belongs to 3 groups; returns (token, [group_id_newest_first])."""
    token, _ = await signup_and_get_token(client, "multi_group_owner@example.com")
    group_ids = []
    for i in range(3):
        r = await client.post(
            "/api/groups",
            json={"event_id": str(test_event.event_id), "name": f"Group {i}"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert r.status_code == 201
        group_ids.append(r.json()["group_id"])
    return token, list(reversed(group_ids))  # newest first


async def test_my_groups_unauthenticated_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/users/me/groups")
    assert r.status_code == 401


async def test_my_groups_empty_for_new_user(
    client: AsyncClient,
    test_event: Event,
) -> None:
    token, _ = await signup_and_get_token(client, "no_groups_user@example.com")
    r = await client.get("/api/users/me/groups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["groups"] == []


async def test_my_groups_returns_all_joined_groups(
    client: AsyncClient,
    multi_group_setup: tuple[str, list[str]],
) -> None:
    token, group_ids = multi_group_setup
    r = await client.get("/api/users/me/groups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    returned_ids = {g["group_id"] for g in r.json()["groups"]}
    assert returned_ids == set(group_ids)


async def test_my_groups_ordered_by_last_active_at_desc(
    client: AsyncClient,
    multi_group_setup: tuple[str, list[str]],
) -> None:
    token, group_ids_newest_first = multi_group_setup
    r = await client.get("/api/users/me/groups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    returned_ids = [g["group_id"] for g in r.json()["groups"]]
    assert returned_ids == group_ids_newest_first


async def test_my_groups_includes_group_i_joined_not_created(
    client: AsyncClient,
    test_event: Event,
) -> None:
    owner_token, _ = await signup_and_get_token(client, "group_maker_b8@example.com")
    r = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id)},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    invite_code = r.json()["invite_code"]
    group_id = r.json()["group_id"]

    joiner_token, _ = await signup_and_get_token(client, "joiner_user_b8@example.com")
    await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {joiner_token}"},
    )

    r2 = await client.get(
        "/api/users/me/groups", headers={"Authorization": f"Bearer {joiner_token}"}
    )
    assert r2.status_code == 200
    returned_ids = {g["group_id"] for g in r2.json()["groups"]}
    assert group_id in returned_ids


async def test_my_groups_response_shape(
    client: AsyncClient,
    test_event: Event,
) -> None:
    token, _ = await signup_and_get_token(client, "shape_tester_b8@example.com")
    await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Shape Test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    r = await client.get("/api/users/me/groups", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    groups = r.json()["groups"]
    assert len(groups) == 1
    g = groups[0]
    for field in (
        "group_id",
        "name",
        "invite_code",
        "event_id",
        "created_by_user_id",
        "last_active_at",
        "archived_at",
        "member_id",
        "joined_at",
    ):
        assert field in g, f"missing field: {field}"


async def test_my_groups_does_not_return_others_groups(
    client: AsyncClient,
    test_event: Event,
) -> None:
    owner_token, _ = await signup_and_get_token(client, "exclusive_owner@example.com")
    await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Private Group"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )

    outsider_token, _ = await signup_and_get_token(client, "outsider_user@example.com")
    r = await client.get(
        "/api/users/me/groups", headers={"Authorization": f"Bearer {outsider_token}"}
    )
    assert r.status_code == 200
    assert r.json()["groups"] == []


async def test_my_groups_join_bumps_order(
    client: AsyncClient,
    test_event: Event,
) -> None:
    """Joining an older group moves it to the top via last_active_at bump."""
    token, _ = await signup_and_get_token(client, "bump_tester@example.com")
    joiner_token, _ = await signup_and_get_token(client, "bump_joiner@example.com")

    r_old = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "Old Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    old_id = r_old.json()["group_id"]
    old_code = r_old.json()["invite_code"]

    r_new = await client.post(
        "/api/groups",
        json={"event_id": str(test_event.event_id), "name": "New Group"},
        headers={"Authorization": f"Bearer {token}"},
    )
    new_id = r_new.json()["group_id"]

    # Joiner joins old group → bumps its last_active_at
    await client.post(
        "/api/groups/join",
        json={"invite_code": old_code},
        headers={"Authorization": f"Bearer {joiner_token}"},
    )

    r = await client.get("/api/users/me/groups", headers={"Authorization": f"Bearer {token}"})
    ids = [g["group_id"] for g in r.json()["groups"]]
    assert ids.index(old_id) < ids.index(new_id)
