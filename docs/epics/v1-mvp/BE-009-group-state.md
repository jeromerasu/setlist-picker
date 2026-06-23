# BE-009 — `GET /api/groups/{invite_code}` (group state + Last-Modified / If-Modified-Since / 304)

**Wave:** 1
**Type:** BE
**Blocked by:** BE-003, BE-006
**Blocks:** FE-005, FE-006, BE-014, BE-017
**ADR references:** [ADR-006 § 3.1 Q1, § 4.14](../../decisions/ADR-006-initial-data-schema.md), [ARCHITECTURE.md § Real-time strategy](../../ARCHITECTURE.md)

## 1. Problem statement

The FE polls this endpoint every 15s while the schedule view is foregrounded to refresh members + picks. The endpoint must return 304 with no body when nothing has changed, so the metered-data cost of an idle group is near-zero.

## 2. Actual solution

`app/services/group_service.get_group_state(db, caller, invite_code) -> tuple[GroupStateResponse, datetime]` returns the payload and the `Last-Modified` instant.

`Last-Modified` is `MAX(pick.server_last_updated_at, member.joined_at)` for the group. Group archival / rename are rare enough that adding `group.updated_at` to the MAX would be overkill for v1; the FE refetches on user navigation regardless. (Note: the comment in `docs/schemas/reference/v1_pydantic.py` mentions `member.left_at` but that column was removed in ADR-006 § 4.28 — we ignore it here.)

The handler:

1. `current_user` dep (BE-003).
2. SELECT Group by `invite_code` (normalized first). If missing → 404 `group_not_found`.
3. Check membership: SELECT Member WHERE `(user_id=caller.id, group_id=group.id)`. If missing → 403 `not_a_member`.
4. Compute `last_modified = MAX(pick.server_last_updated_at, member.joined_at)` — single SQL query with `GREATEST` and subqueries.
5. If request includes `If-Modified-Since` header and the parsed instant >= `last_modified` (truncated to second precision, per HTTP semantics), return **304 Not Modified** with no body and the `Last-Modified` header set.
6. Else, run Q1 from ADR-006 § 3.1 (all active picks + display info) plus a SELECT of all Members. Build `GroupStateResponse`. Return 200 with `Last-Modified` and body.

The picks half of the payload is added by BE-014 (separate ticket because the implementations interleave). BE-009 ships the Members + event summary + `Last-Modified` infrastructure; BE-014 adds `picks: list[PickSummary]`.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/group_service.py` | `get_group_state`, `_compute_last_modified`. |
| `services/api/app/schemas/groups.py` | `GroupStateResponse`, `EventSummary` (copy from reference). |
| `services/api/app/routes/groups.py` | Add `GET /api/groups/{invite_code}`. |
| `services/api/app/utils/http_dates.py` | `parse_if_modified_since(value) -> datetime | None`, `format_last_modified(dt) -> str`. |
| `services/api/tests/test_group_state.py` | See § 7. |
| `services/api/tests/test_http_dates.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoint. |

## 4. Method signatures / new APIs

```python
# app/schemas/groups.py
class EventSummary(_Model):
    event_id: UUID
    name: str
    start_date: date
    end_date: date
    location: str | None
    timezone: str


class PickSummary(_Model):  # populated by BE-014
    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int


class GroupStateResponse(_Model):
    group_id: UUID
    invite_code: str
    name: str
    event: EventSummary
    members: list[MemberOut]
    picks: list[PickSummary]  # BE-014 adds the data; BE-009 returns []
    archived_at: datetime | None
    last_active_at: datetime
```

```python
# app/utils/http_dates.py
def parse_if_modified_since(value: str | None) -> datetime | None:
    """Parse RFC 7231 IMF-fixdate. Returns None on parse failure (be lenient)."""

def format_last_modified(dt: datetime) -> str:
    """Format as IMF-fixdate, e.g. 'Sun, 23 Jun 2026 09:00:00 GMT'."""
```

Endpoint:

| Method | Path | Headers | Response | Status |
|---|---|---|---|---|
| `GET` | `/api/groups/{invite_code}` | `If-Modified-Since` (optional) | `GroupStateResponse` (with `Last-Modified` header) | 200 / 304 / 404 / 403 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 404 | `group_not_found` | Code missing or normalize fails. |
| 403 | `not_a_member` | Caller not a Member of the group. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Header date format | RFC 7231 IMF-fixdate | HTTP/1.1 standard. |
| `If-Modified-Since` precision | 1 second | RFC 7231; sub-second changes might miss a 304. Acceptable per ADR-006 § 4.14. |
| `last_modified` floor | `group.created_at` | If the group has no picks and no member changes after creation, fall back to created_at so the header is never NULL. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Empty group state (no picks, members = creator only) | 200 with members=[creator]; `Last-Modified = creator.joined_at`. |
| `If-Modified-Since` exactly equals `last_modified` truncated to seconds | 304 (RFC 7231 says "not less than"). |
| `If-Modified-Since` is malformed (`"yesterday"`) | Ignore — treat as if header absent; return 200. Lenient per IETF best practice. |
| `If-Modified-Since` is in the future | 304 (server's `last_modified` is in the past relative to the header). |
| Group is archived | Returned with `archived_at != None`. FE renders the badge. |
| Caller's Member row was deleted mid-poll | 403 `not_a_member`. |
| Group's invite code was normalized to fail (bad char) | 404 — same as BE-007. |
| Concurrent pick INSERT during the read | The Q1 query is consistent at the transaction's snapshot; the polled response reflects state at the read. Next poll picks up the new pick. |
| Caller is the creator of the group | No special behavior; same payload. |
| Sub-second pick update — clock didn't advance by 1 s | Edge case: a poll within the same second as a write may 304-skip the update. Next poll (15 s later) picks it up. Acceptable per ADR-006 § 4.14 "rare same-ms churn falls back to a 200 with the fresh payload" — note this is a deliberate simplification; ETag is a v2 upgrade. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `tests/test_http_dates.py` | `test_parse_imf_fixdate_round_trips` | `parse(format(dt)) == dt.replace(microsecond=0)` for several test datetimes. |
| `tests/test_http_dates.py` | `test_parse_invalid_returns_none` | `"yesterday"` → None. |
| `tests/test_http_dates.py` | `test_parse_obsolete_rfc850_format` | `"Sunday, 23-Jun-26 09:00:00 GMT"` → parsed (per RFC 7231 leniency). Optional — implement if cheap; otherwise return None. |
| `tests/test_group_state.py` | `test_get_group_state_returns_members_and_event_summary` | New group → response has the creator in `members[]`, `event` summary populated, `picks=[]`. |
| `tests/test_group_state.py` | `test_get_group_state_sets_last_modified_header` | 200 response has `Last-Modified` header in IMF-fixdate format. |
| `tests/test_group_state.py` | `test_get_group_state_if_modified_since_returns_304` | First call captures `Last-Modified`; second call with that header → 304 with empty body. |
| `tests/test_group_state.py` | `test_get_group_state_if_modified_since_past_returns_200` | `If-Modified-Since` 1 hour before any activity → 200. |
| `tests/test_group_state.py` | `test_get_group_state_after_new_member_joins_returns_200_with_updated_last_modified` | Cache by `Last-Modified`; new Member joins; next poll → 200; new `Last-Modified` is later. |
| `tests/test_group_state.py` | `test_get_group_state_not_member_returns_403` | User who didn't join → 403 `not_a_member`. |
| `tests/test_group_state.py` | `test_get_group_state_unknown_code_returns_404` | Random code → 404. |
| `tests/test_group_state.py` | `test_get_group_state_malformed_if_modified_since_ignored` | Header `"yesterday"` → 200 with body (not 304). |
| `tests/test_group_state.py` | `test_get_group_state_resolves_display_name_via_coalesce` | Override set → MemberOut uses override; override cleared → falls back to user.display_name; neither set → falls back to user.username. |
| `tests/test_group_state.py` | `test_get_group_state_avatar_color_from_user` | MemberOut.avatar_color == user.avatar_color (per ADR-006 § 4.12). |
| `tests/test_group_state.py` | `test_get_group_state_unauthenticated_returns_401` | No header → 401. |

**Manual QA:**

1. `curl -i /api/groups/<code>` → 200 with `Last-Modified`.
2. Re-curl with `-H "If-Modified-Since: <that header>"` → 304.
3. Have another user join → re-curl with old `If-Modified-Since` → 200 with new header.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `group.state_200` | `group_id`, `caller_member_id`, `members_count`, `request_id` (DEBUG) |
| `group.state_304` | `group_id`, `caller_member_id`, `request_id` (DEBUG) |
| `group.state_not_member` | `group_id`, `attempted_user_id`, `request_id` (WARNING) |

## 8. Out of scope

| Item | Where |
|---|---|
| `picks: list[PickSummary]` data | BE-014. |
| ETag upgrade | v2 — ADR-006 § 4.14. |
| Pagination of members for very large groups | Out — group sizes are small in practice. |
| Activity feed | `/api/groups/{invite_code}/activity` is a separate route (BACKLOG-013 — not part of v1). |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. FE-006's 15s poll loop hits 404/405; FE displays the cached snapshot from expo-sqlite. Real-time drift but no data loss.
