"""BE-003: current_user dependency tests via GET /api/users/me."""

from __future__ import annotations

from httpx import AsyncClient


async def _signup_and_get_access_token(client: AsyncClient, email: str) -> str:
    r = await client.post(
        "/api/auth/signup", json={"email": email, "password": "correct horse"}
    )
    assert r.status_code == 201
    return str(r.json()["tokens"]["access_token"])


async def test_no_auth_header_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/users/me")
    assert r.status_code == 401


async def test_invalid_token_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/users/me", headers={"Authorization": "Bearer not.a.real.token"})
    assert r.status_code == 401


async def test_non_bearer_scheme_returns_401(client: AsyncClient) -> None:
    r = await client.get("/api/users/me", headers={"Authorization": "Basic dXNlcjpwYXNz"})
    assert r.status_code == 401


async def test_valid_token_returns_200_with_user(client: AsyncClient) -> None:
    access_token = await _signup_and_get_access_token(client, "deptest@example.com")
    r = await client.get("/api/users/me", headers={"Authorization": f"Bearer {access_token}"})
    assert r.status_code == 200
    assert r.json()["email"] == "deptest@example.com"
