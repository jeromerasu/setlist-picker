"""BE-009: RFC 7231 date helpers."""

from __future__ import annotations

from datetime import datetime, timezone

from app.utils.http_dates import format_last_modified, parse_if_modified_since


def test_format_last_modified_rfc7231() -> None:
    dt = datetime(2026, 6, 23, 12, 34, 56, tzinfo=timezone.utc)
    result = format_last_modified(dt)
    assert result == "Tue, 23 Jun 2026 12:34:56 GMT"


def test_parse_if_modified_since_valid() -> None:
    header = "Tue, 23 Jun 2026 12:34:56 GMT"
    dt = parse_if_modified_since(header)
    assert dt is not None
    assert dt == datetime(2026, 6, 23, 12, 34, 56, tzinfo=timezone.utc)


def test_parse_if_modified_since_malformed_returns_none() -> None:
    assert parse_if_modified_since("not-a-date") is None
