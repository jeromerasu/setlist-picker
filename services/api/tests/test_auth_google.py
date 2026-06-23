"""BE-005: POST /api/auth/google tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from httpx import AsyncClient

from app.auth.palette import AVATAR_PALETTE
from tests.fixtures.rsa_jwks import (
    generate_rsa_private_key,
    make_google_token,
    public_key_to_jwk,
)

_GOOGLE_JWKS_TARGET = "app.auth.google.fetch_jwks"
_CLIENT_ID = "replace-with-google-client-id"


@pytest.fixture(scope="module")
def google_key() -> RSAPrivateKey:
    return generate_rsa_private_key()


@pytest.fixture(scope="module")
def google_jwk(google_key: RSAPrivateKey) -> dict[str, Any]:
    return public_key_to_jwk(google_key, kid="test-kid")


def _mock_jwks(jwk_dict: dict[str, Any]) -> AsyncMock:
    return AsyncMock(return_value=[jwk_dict])


async def test_google_new_user_returns_201(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.new.001")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["auth_provider"] == "google"
    assert "access_token" in body["tokens"]


async def test_google_existing_user_returns_200(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.existing.001")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r1 = await client.post("/api/auth/google", json={"id_token": token})
        assert r1.status_code == 201
        r2 = await client.post("/api/auth/google", json={"id_token": token})
    assert r2.status_code == 200
    assert r1.json()["user"]["id"] == r2.json()["user"]["id"]


async def test_google_invalid_token_returns_401(client: AsyncClient) -> None:
    with patch(_GOOGLE_JWKS_TARGET, AsyncMock(return_value=[])):
        r = await client.post("/api/auth/google", json={"id_token": "not.a.jwt"})
    assert r.status_code == 401


async def test_google_expired_token_returns_401(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.expired.001", exp_offset=-60)
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 401


async def test_google_wrong_audience_returns_401(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.audience.001", client_id="wrong-client")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 401


async def test_google_wrong_issuer_returns_401(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.issuer.001", iss="https://evil.example.com")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 401


async def test_google_accepts_accounts_google_com_issuer(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    """Both 'accounts.google.com' (without https) and the https form are valid."""
    token = make_google_token(google_key, sub="google.iss.short.001", iss="accounts.google.com")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 201


async def test_google_user_has_google_auth_provider(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.provider.001")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["auth_provider"] == "google"


async def test_google_email_from_token_used_if_payload_missing(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(
        google_key, sub="google.email.token.001", email="from_token@gmail.com"
    )
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "from_token@gmail.com"


async def test_google_email_from_payload_overrides_token_email(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.email.override.001", email="token@gmail.com")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post(
            "/api/auth/google",
            json={"id_token": token, "email": "payload@example.com"},
        )
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "payload@example.com"


async def test_google_no_email_creates_user_without_email(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.noemail.001", email=None)
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["email"] is None


async def test_google_display_name_from_payload(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.displayname.001")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post(
            "/api/auth/google",
            json={"id_token": token, "display_name": "Jerome R."},
        )
    assert r.status_code == 201
    assert r.json()["user"]["display_name"] == "Jerome R."


async def test_google_unknown_kid_returns_401(
    client: AsyncClient,
    google_key: RSAPrivateKey,
) -> None:
    wrong_jwk = public_key_to_jwk(google_key, kid="wrong-kid")
    token = make_google_token(google_key, sub="google.kid.001", kid="test-kid")
    with patch(_GOOGLE_JWKS_TARGET, AsyncMock(return_value=[wrong_jwk])):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 401
    assert r.json()["detail"]["error_code"] == "google_key_not_found"


async def test_google_creates_avatar_color_from_palette(
    client: AsyncClient,
    google_key: RSAPrivateKey,
    google_jwk: dict[str, Any],
) -> None:
    token = make_google_token(google_key, sub="google.avatar.001")
    with patch(_GOOGLE_JWKS_TARGET, _mock_jwks(google_jwk)):
        r = await client.post("/api/auth/google", json={"id_token": token})
    assert r.status_code == 201
    assert r.json()["user"]["avatar_color"] in AVATAR_PALETTE
