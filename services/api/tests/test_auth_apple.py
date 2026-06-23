"""BE-004: POST /api/auth/apple tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from httpx import AsyncClient

from app.auth.palette import AVATAR_PALETTE
from tests.fixtures.rsa_jwks import (
    generate_rsa_private_key,
    make_apple_token,
    public_key_to_jwk,
)

_APPLE_JWKS_TARGET = "app.auth.apple.fetch_jwks"
_BUNDLE_ID = "com.setlistpicker.app"


@pytest.fixture(scope="module")
def apple_key() -> RSAPrivateKey:
    return generate_rsa_private_key()


@pytest.fixture(scope="module")
def apple_jwk(apple_key: RSAPrivateKey) -> dict[str, Any]:
    return public_key_to_jwk(apple_key, kid="test-kid")


def _mock_jwks(jwk_dict: dict[str, Any]) -> AsyncMock:
    return AsyncMock(return_value=[jwk_dict])


async def test_apple_new_user_returns_201(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.new.001")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["auth_provider"] == "apple"
    assert "access_token" in body["tokens"]


async def test_apple_existing_user_returns_200(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.existing.001")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r1 = await client.post("/api/auth/apple", json={"identity_token": token})
        assert r1.status_code == 201
        r2 = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r2.status_code == 200
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]


async def test_apple_invalid_token_returns_401(client: AsyncClient) -> None:
    with patch(_APPLE_JWKS_TARGET, AsyncMock(return_value=[])):
        r = await client.post("/api/auth/apple", json={"identity_token": "not.a.jwt"})
    assert r.status_code == 401


async def test_apple_expired_token_returns_401(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.expired.001", exp_offset=-60)
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 401


async def test_apple_wrong_audience_returns_401(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.audience.001", bundle_id="com.wrong.bundle")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 401


async def test_apple_wrong_issuer_returns_401(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.issuer.001", iss="https://evil.example.com")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 401


async def test_apple_user_has_apple_auth_provider(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.provider.001")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["auth_provider"] == "apple"


async def test_apple_email_from_token_used_if_payload_missing(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.email.token.001", email="from_token@apple.com")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "from_token@apple.com"


async def test_apple_email_from_payload_overrides_token_email(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.email.override.001", email="token@apple.com")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post(
            "/api/auth/apple",
            json={"identity_token": token, "email": "payload@example.com"},
        )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "payload@example.com"


async def test_apple_no_email_creates_user_without_email(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.noemail.001", email=None)
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["email"] is None


async def test_apple_display_name_from_payload(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.displayname.001")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post(
            "/api/auth/apple",
            json={"identity_token": token, "display_name": "Jerome R."},
        )
    assert r.status_code == 201
    assert r.json()["user"]["display_name"] == "Jerome R."


async def test_apple_unknown_kid_returns_401(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
) -> None:
    wrong_jwk = public_key_to_jwk(apple_key, kid="wrong-kid")
    token = make_apple_token(apple_key, sub="apple.kid.001", kid="test-kid")
    with patch(_APPLE_JWKS_TARGET, AsyncMock(return_value=[wrong_jwk])):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "apple_key_not_found"


async def test_apple_creates_avatar_color_from_palette(
    client: AsyncClient,
    apple_key: RSAPrivateKey,
    apple_jwk: dict[str, Any],
) -> None:
    token = make_apple_token(apple_key, sub="apple.avatar.001")
    with patch(_APPLE_JWKS_TARGET, _mock_jwks(apple_jwk)):
        r = await client.post("/api/auth/apple", json={"identity_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["avatar_color"] in AVATAR_PALETTE
