"""BE-018: artist_normalize.py unit tests."""

from __future__ import annotations

from app.services.artist_normalize import normalize


def test_normalize_lowercases() -> None:
    assert normalize("EFFIN") == "effin"


def test_normalize_strips_diacritics() -> None:
    assert normalize("Beyoncé") == "beyonce"


def test_normalize_collapses_whitespace() -> None:
    assert normalize("  Close   Friends   Only  ") == "close friends only"


def test_normalize_unicode_nfkd() -> None:
    # fi ligature → f + i
    assert normalize("ﬁve") == "five"


def test_normalize_multiple_transforms() -> None:
    assert normalize("  BJÖRK  ") == "bjork"


def test_normalize_empty_string() -> None:
    assert normalize("") == ""
