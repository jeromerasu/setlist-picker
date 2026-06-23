# BE-008 — `GET /api/users/me/groups` (caller's group list)

**Wave:** 1
**Type:** BE
**Blocked by:** BE-003
**Blocks:** FE-001
**ADR references:** [ADR-006 § 3.1 Q3](../../decisions/ADR-006-initial-data-schema.md), [ARCHITECTURE.md § API surface](../../ARCHITECTURE.md)

## 1. Problem statement

The Home screen needs every group the signed-in user is a Member of, sorted by recency. One request → one render.

## 2. Actual solution

Single endpoint. `app/services/group_service.list_my_groups(db, user) -> list[MyGroupListItem]` runs Q3 from ADR-006 § 3.1 with a JOIN to `member` so we can hand the FE both the group payload and the caller's `member_id` + `joined_at`.

Returned ordering: `g.last_active_at DESC`. Archived groups appear at the bottom (where `archived_at IS NOT NULL`); v1 has none yet, but FE-001 reads `archived_at` to show a badge.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/group_service.py` | Add `list_my_groups`. |
| `services/api/app/schemas/groups.py` | Add `MyGroupListResponse`. (`MyGroupListItem` already added in BE-007.) |
| `services/api/app/routes/users.py` | Add `GET /api/users/me/groups`. |
| `services/api/tests/test_my_groups.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoint. |

## 4. Method signatures / new APIs

```python
# app/schemas/groups.py
class MyGroupListResponse(_Model):
    groups: list[MyGroupListItem]
```

```python
# app/services/group_service.py
async def list_my_groups(db: AsyncSession, user: User) -> list[MyGroupListItem]: ...
```

Endpoint:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `GET` | `/api/users/me/groups` | — | `MyGroupListResponse` | 200 |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Ordering | `g.last_active_at DESC, g.created_at DESC` (tiebreaker) | Most-recently-active first; deterministic on ties for screenshot stability. |
| Pagination | None in v1 | Users are unlikely to be in > 50 groups; bounded by reasonable use. Document as forward-compat. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| User in zero groups | 200; `{"groups": []}`. FE-001 renders the empty state. |
| User has 100+ groups | All returned. Sort order stable. No truncation in v1. |
| User has an archived group (`archived_at IS NOT NULL`) | Included; sorted by `last_active_at` (archived groups usually have older `last_active_at` so they sink). |
| Group created by a different user, but caller is a Member | Returned. (Membership, not authorship, is the filter.) |
| Caller's Member row was just hard-deleted (race) | Not returned (the JOIN doesn't match). |
| Caller is unauthenticated | 401 `invalid_token`. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_my_groups_empty_returns_200_with_empty_list` | Fresh user → `{"groups": []}`. |
| `test_my_groups_returns_all_member_groups` | User joined 3 groups → all 3 in response. |
| `test_my_groups_sorted_by_last_active_desc` | Seed `last_active_at` values; response order matches. |
| `test_my_groups_tiebreaker_on_created_at_desc` | Two groups with identical `last_active_at`; the more recently created comes first. |
| `test_my_groups_includes_member_id_and_joined_at` | Each item has the caller's member_id and the joined_at timestamp. |
| `test_my_groups_excludes_groups_user_left` | User joined → left (hard delete) → list excludes that group. |
| `test_my_groups_includes_archived_groups` | Archived group → present in response; `archived_at` field non-null. |
| `test_my_groups_unauthenticated_returns_401` | No header → 401. |
| `test_my_groups_only_returns_callers_groups_not_other_users` | User A is in 2 groups; User B is in 1 group; calling as A returns A's 2 only. |

**Manual QA:**

1. As User A with no groups: `curl /api/users/me/groups` → empty list.
2. Create a group, join another → both appear.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `groups.list_my_groups` | `user_id`, `count`, `request_id` (DEBUG) |

## 8. Out of scope

| Item | Where |
|---|---|
| Cursor pagination | Forward-compat; not v1. |
| Per-group unread badge counts | BACKLOG-012. |
| Search / filter | Out — FE-001 renders the full list. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. Home screen breaks until reverted; no data loss.
