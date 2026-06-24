"""BE-003: POST /api/auth/signup tests."""

from __future__ import annotations

from httpx import AsyncClient

from app.auth.palette import AVATAR_PALETTE


async def test_signup_local_returns_201_with_user_and_tokens(
    client: AsyncClient,
) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": "jerome@example.com", "password": "correct horse"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "jerome@example.com"
    assert "access_token" in body["tokens"]
    assert "refresh_token" in body["tokens"]


async def test_signup_lowercases_email(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": "J@Foo.com", "password": "correct horse"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "j@foo.com"


async def test_signup_assigns_avatar_color_from_palette(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": "coloruser@example.com", "password": "correct horse"},
    )
    assert r.status_code == 201
    assert r.json()["user"]["avatar_color"] in AVATAR_PALETTE


async def test_signup_duplicate_email_returns_400(client: AsyncClient) -> None:
    payload = {"email": "shared@x.com", "password": "correct horse"}
    r1 = await client.post("/api/auth/signup", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/auth/signup", json=payload)
    assert r2.status_code == 400
    assert r2.json()["detail"]["error_code"] == "email_taken"


async def test_signup_case_insensitive_email_collision(client: AsyncClient) -> None:
    r1 = await client.post(
        "/api/auth/signup",
        json={"email": "CaseUser@Example.COM", "password": "correct horse"},
    )
    assert r1.status_code == 201
    r2 = await client.post(
        "/api/auth/signup",
        json={"email": "caseuser@example.com", "password": "correct horse"},
    )
    assert r2.status_code == 400
    assert r2.json()["detail"]["error_code"] == "email_taken"


async def test_signup_invalid_email_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": "notanemail", "password": "correct horse"},
    )
    assert r.status_code == 422


async def test_signup_short_password_returns_422(client: AsyncClient) -> None:
    r = await client.post(
        "/api/auth/signup",
        json={"email": "shortpw@example.com", "password": "1234567"},
    )
    assert r.status_code == 422
