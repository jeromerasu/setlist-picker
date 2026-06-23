from __future__ import annotations

import secrets
from typing import Final

CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

_NORMALIZE_MAP: Final[dict[str, str]] = {"I": "1", "L": "1", "O": "0"}


def generate_invite_code() -> str:
    """Return 8 cryptographically-random chars from CROCKFORD_ALPHABET."""
    return "".join(secrets.choice(CROCKFORD_ALPHABET) for _ in range(8))


def normalize(raw: str) -> str:
    """Uppercase + Crockford substitutions: I→1, L→1, O→0."""
    upper = raw.upper()
    return "".join(_NORMALIZE_MAP.get(c, c) for c in upper)
