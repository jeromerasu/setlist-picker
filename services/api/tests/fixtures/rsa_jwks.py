"""Helpers for generating RSA test keys and signed JWTs for Apple/Google tests."""

from __future__ import annotations

import time
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
from jose import jwk, jwt


def generate_rsa_private_key() -> RSAPrivateKey:
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def private_key_to_pem(key: RSAPrivateKey) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def public_key_to_jwk(key: RSAPrivateKey, kid: str = "test-kid") -> dict[str, Any]:
    """Return a JWK dict for the public half of key."""
    pub_pem = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    constructed = jwk.construct(pub_pem, algorithm="RS256")
    d: dict[str, Any] = dict(constructed.to_dict())
    d["kid"] = kid
    d["use"] = "sig"
    d["alg"] = "RS256"
    return d


def make_apple_token(
    private_key: RSAPrivateKey,
    *,
    sub: str = "apple.user.001",
    bundle_id: str = "com.setlistpicker.app",
    email: str | None = "user@private.appleid.com",
    kid: str = "test-kid",
    iss: str = "https://appleid.apple.com",
    exp_offset: int = 3600,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": iss,
        "aud": bundle_id,
        "iat": now,
        "exp": now + exp_offset,
    }
    if email is not None:
        payload["email"] = email
    private_pem = private_key_to_pem(private_key)
    return str(jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid}))


def make_google_token(
    private_key: RSAPrivateKey,
    *,
    sub: str = "google.user.001",
    client_id: str = "replace-with-google-client-id",
    email: str | None = "user@gmail.com",
    kid: str = "test-kid",
    iss: str = "https://accounts.google.com",
    exp_offset: int = 3600,
) -> str:
    now = int(time.time())
    payload: dict[str, Any] = {
        "sub": sub,
        "iss": iss,
        "aud": client_id,
        "iat": now,
        "exp": now + exp_offset,
    }
    if email is not None:
        payload["email"] = email
    private_pem = private_key_to_pem(private_key)
    return str(jwt.encode(payload, private_pem, algorithm="RS256", headers={"kid": kid}))
