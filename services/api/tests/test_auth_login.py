"""BE-003: POST /api/auth/login tests."""

from __future__ import annotations

from httpx import AsyncClient


async def _signup(client: AsyncClient, username: str, password: str = "correct horse") -> None:
    r = await client.post("/api/auth/signup", json={"username": username, "password": password})
    assert r.status_code == 201


async def test_login_valid_credentials_returns_200_with_tokens(client: AsyncClient) -> None:
    await _signup(client, "loginuser")
    r = await client.post(
        "/api/auth/login", json={"username": "loginuser", "password": "correct horse"}
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]
    assert body["user"]["username"] == "loginuser"


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await _signup(client, "wrongpwuser")
    r = await client.post(
        "/api/auth/login", json={"username": "wrongpwuser", "password": "wrong password"}
    )
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_credentials"


async def test_login_unknown_user_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/login",
        json={"username": "nosuchuser", "password": "doesnotmatter"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_credentials"


async def test_login_unknown_user_does_not_leak_existence(client: AsyncClient) -> None:
    """Both user-not-found and wrong-password must return the same error_code."""
    r_bad_user = await client.post(
        "/api/auth/login",
        json={"username": "ghost_user_xyz", "password": "correct horse"},
    )
    await _signup(client, "realuserx")
    r_bad_pw = await client.post(
        "/api/auth/login", json={"username": "realuserx", "password": "wrong password"}
    )
    assert r_bad_user.status_code == r_bad_pw.status_code == 401
    assert (
        r_bad_user.json()["detail"]["error_code"]
        == r_bad_pw.json()["detail"]["error_code"]
        == "invalid_credentials"
    )


async def test_login_case_insensitive_username(client: AsyncClient) -> None:
    await _signup(client, "MixedCase")
    r = await client.post(
        "/api/auth/login",
        json={"username": "MixedCase", "password": "correct horse"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["username"] == "mixedcase"
