# BE-012 — `GET /api/events` (list + search)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-002
**Blocks:** FE-003
**ADR references:** [ADR-006 § 2.4](../../decisions/ADR-006-initial-data-schema.md), [ARCHITECTURE.md § API surface](../../ARCHITECTURE.md)

## 1. Problem statement

The Event Picker screen (`isEventPicker`) needs a flat list of available festivals, with text search across name + location. v1 source is the curated seed populated by BE-018 (per EPIC OQ-03).

## 2. Actual solution

Single endpoint, single query.

`GET /api/events?q={string}` — `q` is optional. When absent or empty, return all events ordered by `start_date ASC` (festivals coming up first). When present, filter via `name ILIKE %q% OR location ILIKE %q%`. Trim `q` and lowercase both sides for the ILIKE.

Pagination: not in v1 (curated list ≈ 10 events).

Response shape matches `EventListResponse` from `docs/schemas/reference/v1_pydantic.py`.

Authenticated — `Depends(current_user)`. The endpoint requires a token but doesn't filter by user; we don't want unauth'd scrapers walking the event list.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/event_service.py` | New file — `list_events(db, q: str | None)`. |
| `services/api/app/schemas/events.py` | `EventListItem`, `EventListResponse`. |
| `services/api/app/routes/events.py` | New file — `GET /api/events`. |
| `services/api/app/main.py` | Include the events router. |
| `services/api/tests/test_events_list.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoint. |

## 4. Method signatures / new APIs

```python
# app/schemas/events.py
class EventListItem(_Model):
    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str


class EventListResponse(_Model):
    events: list[EventListItem]
```

```python
# app/services/event_service.py
async def list_events(db: AsyncSession, q: str | None) -> list[EventListItem]: ...
```

Endpoint:

| Method | Path | Query | Response | Status |
|---|---|---|---|---|
| `GET` | `/api/events` | `?q=` (optional string) | `EventListResponse` | 200 |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Ordering | `start_date ASC, name ASC` (tiebreak) | Coming-up first; deterministic. |
| `q` max length | 80 chars | Prevent malformed long queries; matches event name limit. |
| Search collation | `ILIKE %q%` | Postgres case-insensitive; sufficient for v1. No FTS. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| `q` absent | Return all events. |
| `q=""` | Treat as absent. |
| `q="   "` | Trim → treat as absent. |
| `q="EDC"` | Match "EDC Las Vegas 2026" by name. |
| `q="vegas"` | Match by location ("Las Vegas, NV"). |
| `q="EdC vEgAs"` (mixed case) | Case-insensitive match. |
| `q="something else"` | Returns `{"events": []}`. |
| `q` contains SQL wildcards (`%`, `_`) | Escape before ILIKE OR use parameterized binding — SQLAlchemy escapes automatically, but verify the test covers `q="50%"`. |
| `q` contains unicode | Postgres ILIKE works with unicode; no special handling needed. |
| Caller unauthenticated | 401. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_list_events_no_query_returns_all_sorted` | Seed 3 events with distinct start_dates; response order is earliest-first. |
| `test_list_events_query_matches_name` | `q="EDC"` → 1 event whose name contains "EDC". |
| `test_list_events_query_matches_location` | `q="Las Vegas"` → matches by location. |
| `test_list_events_query_case_insensitive` | `q="edc"` and `q="EDC"` → same result. |
| `test_list_events_empty_query_returns_all` | `q=""` and `q="   "` → all events. |
| `test_list_events_no_match_returns_empty` | `q="zzz"` → `[]`. |
| `test_list_events_sql_wildcard_in_query_is_literal` | `q="50%"` does not match all events — `%` is escaped. |
| `test_list_events_unauthenticated_returns_401` | No header → 401. |

**Manual QA:**

1. Seed: `psql ... -c "insert into event (...) values ('EDC Las Vegas 2026', ...)..."`.
2. `curl -H "authorization: Bearer $TOKEN" /api/events` → list.
3. `curl ".../api/events?q=vegas"` → filtered.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `events.listed` | `q: str | None`, `result_count: int`, `request_id` (DEBUG) |

## 8. Out of scope

| Item | Where |
|---|---|
| Full-text search | BACKLOG-015. |
| Featured / pinned events | OQ-03 — handled by seed ordering. |
| Event detail endpoint | BE-013. |
| User-submitted events | v2. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. FE-003 falls back to its in-memory `EVENTS` constant if any. Acceptable.
