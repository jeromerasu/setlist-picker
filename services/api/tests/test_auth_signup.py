"""BE-003: POST /api/auth/signup tests."""

from __future__ import annotations

from httpx import AsyncClient

from app.auth.palette import AVATAR_PALETTE


async def test_signup_local_returns_201_with_user_and_tokens(
    client: AsyncClient,
) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"username": "jerome", "password": "correct horse"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["username"] == "jerome"
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]


async def test_signup_lowercases_username(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"username": "JeromeUpper", "password": "correct horse"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["username"] == "jeromeupper"


async def test_signup_lowercases_email(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"username": "emailtest", "password": "correct horse", "email": "J@Foo.com"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "j@foo.com"


async def test_signup_assigns_avatar_color_from_palette(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"username": "coloruser", "password": "correct horse"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["avatar_color"] in AVATAR_PALETTE


async def test_signup_duplicate_username_returns_400(client: AsyncClient) -> None:
    payload = {"username": "dupuser", "password": "correct horse"}
    r1 = await client.post("/api/auth/signup", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/auth/signup", json=payload)
    assert r2.status_code == 400
    assert r2.json()["detail"]["error_code"] == "username_taken"


async def test_signup_duplicate_email_returns_400(client: AsyncClient) -> None:
    r1 = await client.post(
        "/api/auth/signup",
        json={"username": "emaila", "password": "correct horse", "email": "shared@x.com"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/auth/signup",
        json={"username": "emailb", "password": "correct horse", "email": "shared@x.com"},
    )
    assert r2.status_code == 400
    assert r2.json()["detail"]["error_code"] == "email_taken"


async def test_signup_case_insensitive_username_collision(client: AsyncClient) -> None:
    r1 = await client.post(
        "/api/auth/signup",
        json={"username": "CaseUser", "password": "correct horse"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/auth/signup",
        json={"username": "caseuser", "password": "correct horse"},
    )
    assert r2.status_code == 400


async def test_signup_invalid_username_chars_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"username": "jerome!", "password": "correct horse"},
    )
    assert r.status_code == 422


async def test_signup_short_password_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"username": "shortpw", "password": "1234567"},
    )
    assert r.status_code == 422
