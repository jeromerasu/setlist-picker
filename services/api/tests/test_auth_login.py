"""BE-003: POST /api/auth/login tests."""

from __future__ import annotations

from httpx import AsyncClient


async def _signup(client: AsyncClient, email: str, password: str = "correct horse") -> None:
    r = await client.post("/api/auth/signup", json={"email": email, "password": password})
    assert r.status_code == 201


async def test_login_valid_credentials_returns_200_with_tokens(client: AsyncClient) -> None:
    await _signup(client, "loginuser@example.com")
    r = await client.post(
        "/api/auth/login", json={"email": "loginuser@example.com", "password": "correct horse"}
    )
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]
    assert body["user"]["email"] == "loginuser@example.com"


async def test_login_wrong_password_returns_401(client: AsyncClient) -> None:
    await _signup(client, "wrongpwuser@example.com")
    r = await client.post(
        "/api/auth/login", json={"email": "wrongpwuser@example.com", "password": "wrong password"}
    )
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_credentials"


async def test_login_unknown_user_returns_401(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/login",
        json={"email": "nosuchuser@example.com", "password": "doesnotmatter"},
    )
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "invalid_credentials"


async def test_login_unknown_user_does_not_leak_existence(client: AsyncClient) -> None:
    """Both user-not-found and wrong-password must return the same error_code."""
    r_bad_user = await client.post(
        "/api/auth/login",
        json={"email": "ghost@example.com", "password": "correct horse"},
    )
    await _signup(client, "realuserx@example.com")
    r_bad_pw = await client.post(
        "/api/auth/login", json={"email": "realuserx@example.com", "password": "wrong password"}
    )
    assert r_bad_user.status_code == r_bad_pw.status_code == 401
    assert (
        r_bad_user.json()["detail"]["error_code"]
        == r_bad_pw.json()["detail"]["error_code"]
        == "invalid_credentials"
    )


async def test_login_case_insensitive_email(client: AsyncClient) -> None:
    await _signup(client, "MixedCase@Example.COM")
    r = await client.post(
        "/api/auth/login",
        json={"email": "mixedcase@example.com", "password": "correct horse"},
    )
    assert r.status_code == 200
    assert r.json()["user"]["email"] == "mixedcase@example.com"
