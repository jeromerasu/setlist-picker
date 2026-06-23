from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime


def format_last_modified(dt: datetime) -> str:
    """Format datetime as RFC 7231 IMF-fixdate (e.g. 'Tue, 23 Jun 2026 12:34:56 GMT')."""
    utc = dt.astimezone(timezone.utc)
    return format_datetime(utc, usegmt=True)


def parse_if_modified_since(header: str) -> datetime | None:
    """Parse an If-Modified-Since header value; return None if malformed."""
    try:
        dt = parsedate_to_datetime(header)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None
