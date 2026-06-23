"""BE-003: POST /api/auth/refresh tests."""

from __future__ import annotations

from httpx import AsyncClient


async def _signup_and_get_refresh_token(client: AsyncClient, username: str) -> str:
    r = await client.post(
        "/api/auth/signup", json={"username": username, "password": "correct horse"}
    )
    assert r.status_code == 201
    return str(r.json()["tokens"]["refresh_token"])


async def test_refresh_valid_token_returns_new_pair(client: AsyncClient) -> None:
    refresh_token = await _signup_and_get_refresh_token(client, "refreshuser1")
    r = await client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


async def test_refresh_access_token_rejected(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"username": "refreshuser2", "password": "correct horse"},
    )
    access_token = r.json()["tokens"]["access_token"]
    r2 = await client.post("/api/auth/refresh", json={"refresh_token": access_token})
    assert r2.status_code == 401
    assert r2.json()["detail"]["error_code"] == "invalid_token"


async def test_refresh_garbage_token_returns_401(client: AsyncClient) -> None:
    r = await client.post("/api/auth/refresh", json={"refresh_token": "not.a.token"})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_token"
