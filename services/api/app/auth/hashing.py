from __future__ import annotations

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_ph = PasswordHasher(memory_cost=65536, time_cost=3, parallelism=4)

_KNOWN_BAD_HASH = _ph.hash("__setlist_picker_sentinel__")


def hash_password(plain: str) -> str:
    return _ph.hash(plain)


def verify_password(plain: str, encoded: str) -> bool:
    """Returns True if plain matches encoded. Constant-time on mismatch.

    Raises nothing — callers check the return value.
    """
    try:
        return _ph.verify(encoded, plain)
    except VerifyMismatchError:
        return False


def dummy_verify() -> None:
    """Run a full argon2 verify against a sentinel hash.

    Called on login-not-found paths to prevent timing-based user enumeration.
    """
    try:
        _ph.verify(_KNOWN_BAD_HASH, "__not_a_real_password__")
    except VerifyMismatchError:
        pass
