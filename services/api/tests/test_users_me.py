"""BE-003: GET /api/users/me and PATCH /api/users/me tests."""

from __future__ import annotations

from httpx import AsyncClient


async def _signup(
    client: AsyncClient, username: str, password: str = "correct horse"
) -> tuple[str, str]:
    """Returns (access_token, user_id)."""
    r = await client.post("/api/auth/signup", json={"username": username, "password": password})
    assert r.status_code == 201
    body = r.json()
    return str(body["tokens"]["access_token"]), str(body["user"]["id"])


async def test_get_me_returns_user_fields(client: AsyncClient) -> None:
    access_token, _ = await _signup(client, "meuser1")
    r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "meuser1"
    assert body["auth_provider"] == "local"
    assert "id" in body
    assert "avatar_color" in body


async def test_patch_me_updates_display_name(client: AsyncClient) -> None:
    access_token, _ = await _signup(client, "meuser2")
    r = await client.patch(
        "/api/users/me",
        json={"display_name": "Jerome R."},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200
    assert r.json()["display_name"] == "Jerome R."


async def test_patch_me_updates_avatar_color(client: AsyncClient) -> None:
    access_token, _ = await _signup(client, "meuser3")
    r = await client.patch(
        "/api/users/me",
        json={"avatar_color": "#FF5733"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 200
    assert r.json()["avatar_color"] == "#FF5733"


async def test_patch_me_invalid_avatar_color_returns_422(client: AsyncClient) -> None:
    access_token, _ = await _signup(client, "meuser4")
    r = await client.patch(
        "/api/users/me",
        json={"avatar_color": "red"},
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert r.status_code == 422
