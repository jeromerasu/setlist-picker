"""BE-006: Crockford invite-code helpers."""

from __future__ import annotations

from app.auth.invite_code import CROCKFORD_ALPHABET, generate_invite_code, normalize


def test_generate_invite_code_length() -> None:
    assert len(generate_invite_code()) == 8


def test_generate_invite_code_chars_in_alphabet() -> None:
    code = generate_invite_code()
    assert all(c in CROCKFORD_ALPHABET for c in code)


def test_generate_invite_code_different_each_call() -> None:
    codes = {generate_invite_code() for _ in range(50)}
    # Statistically impossible for all 50 to be identical
    assert len(codes) > 1


def test_normalize_uppercase() -> None:
    assert normalize("abcdefgh") == "ABCDEFGH"


def test_normalize_i_l_to_1_o_to_0() -> None:
    # I→1, O→0, L→1 ⟹ "IOLiol" (uppercased "IOLIOL") → "101101"
    assert normalize("IOLiol") == "101101"


def test_normalize_mixed() -> None:
    # I→1, O→0: "A1B2I3O4" → "A1B21304"
    assert normalize("A1B2I3O4") == "A1B21304"
    assert normalize("il") == "11"
