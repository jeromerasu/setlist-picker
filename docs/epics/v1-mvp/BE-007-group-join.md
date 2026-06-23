# BE-007 — `POST /api/groups/join` (idempotent join by invite code)

**Wave:** 1
**Type:** BE
**Blocked by:** BE-003, BE-006
**Blocks:** FE-004
**ADR references:** [ADR-006 § 2.3, § 4.11, § 4.22, § 4.27](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

A signed-in user enters an 8-char invite code to join a group. Server normalizes the code, resolves the Group, creates a Member row for `(current_user, group)` if none exists, and logs `member_joined`. If the user is already a Member, the endpoint is **idempotent** — returns the existing Member with `is_new_member=false`.

## 2. Actual solution

`app/services/group_service.py`'s `join_group(db, joiner, raw_invite_code, display_name_override) -> GroupJoinResponse`.

Algorithm:

1. `normalized = invite_code.normalize(raw_invite_code)`. Validate length 8 + alphabet. If invalid → 404 `group_not_found` (do **not** distinguish "malformed code" from "no such code" — both leak signal about the code space).
2. SELECT Group WHERE `invite_code = normalized`. If missing → 404 `group_not_found`.
3. SELECT Member WHERE `(user_id=joiner.id, group_id=group.id)`. If found:
   - Return `GroupJoinResponse(group=..., member=..., is_new_member=False)`. Do **not** overwrite `display_name_override` even if one is provided — second-time joins are read-only.
4. If not found:
   - INSERT a new Member row.
   - INSERT a `group_activity` row of kind `member_joined` with payload `{display_name, avatar_color}` (denormalized from the joining user).
   - Update `group.last_active_at = now()`.
   - Return `GroupJoinResponse(..., is_new_member=True)`.

The MyGroupListItem nested in the response comes from a shared resolver — see `app/services/group_service.resolve_my_group_item(group, member)`.

Concurrency: two simultaneous joins by the same `(user_id, group_id)` pair — both attempt INSERT, second hits the `uq_member_user_group` unique index → IntegrityError → caught → re-SELECT → return the existing row. The endpoint never returns 500 for this collision.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/group_service.py` | `join_group`, `resolve_my_group_item`. |
| `services/api/app/schemas/groups.py` | `GroupJoinRequest`, `MemberOut`, `MyGroupListItem`, `GroupJoinResponse` (copy from reference). |
| `services/api/app/routes/groups.py` | Add `POST /api/groups/join`. |
| `services/api/tests/test_group_join.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add `/api/groups/join`. |

## 4. Method signatures / new APIs

```python
# app/schemas/groups.py
class GroupJoinRequest(_Model):
    invite_code: str = Field(min_length=8, max_length=8)
    display_name_override: str | None = Field(default=None, min_length=1, max_length=80)


class MemberOut(_Model):
    member_id: UUID
    user_id: UUID
    group_id: UUID
    display_name: str  # resolved: override → user.display_name → user.username
    display_name_override: str | None
    avatar_color: str
    joined_at: datetime


class MyGroupListItem(_Model):
    group_id: UUID
    name: str
    invite_code: str
    event_id: UUID
    created_by_user_id: UUID
    last_active_at: datetime
    archived_at: datetime | None
    member_id: UUID
    joined_at: datetime


class GroupJoinResponse(_Model):
    group: MyGroupListItem
    member: MemberOut
    is_new_member: bool
```

```python
# app/services/group_service.py
async def join_group(
    db: AsyncSession,
    joiner: User,
    raw_invite_code: str,
    display_name_override: str | None,
) -> GroupJoinResponse: ...
```

Endpoint:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `POST` | `/api/groups/join` | `GroupJoinRequest` | `GroupJoinResponse` | 200 (existing member) / 201 (newly joined) |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 404 | `group_not_found` | Code doesn't resolve OR is malformed (we don't distinguish). |
| 422 | (Pydantic) | `invite_code` length wrong, `display_name_override` length wrong. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Status code on new join | 201 | Distinguishes "newly joined" from "re-confirming existing membership." |
| Status code on idempotent | 200 | Per REST conventions. |
| Update `group.last_active_at` on new join only? | Yes — only on new join | Idempotent re-call shouldn't bump the archival clock. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Code with lowercase letters (`"k7m2x9pq"`) | Normalize uppercases → resolves. |
| Code with `I` / `L` / `O` from user typo | Normalize maps to `1`/`1`/`0` → may resolve to a valid group. Acceptable per Crockford's intended decoding. |
| Code shorter than 8 chars | 404 — don't 422; we don't want to leak code-space info. (The FE 's input is `maxlength=8` per the prototype.) |
| Code containing characters outside the Crockford alphabet (e.g. `"K7M2X9P!"` after normalize) | After normalize, `!` is still `!`; the SELECT misses → 404. |
| Group is archived (`archived_at IS NOT NULL`) | Still join — archival is read-only flag for the sweep; the FE will show the badge. v1 doesn't have archived groups yet (no cron). Document as forward-compat. |
| User already a Member | 200 with `is_new_member=False`; do not bump `last_active_at`; do not write `member_joined` activity. |
| User left the group previously (Member hard-deleted) | A fresh INSERT creates a new Member row with a new `id` and `joined_at`. Per ADR-006 § 4.15. |
| Two concurrent first-time joins for same `(user, group)` | Second hits unique index → caught + re-select returns the same row; both responses are 200/201 with same member_id. The "won" side gets 201; "lost" side gets 200. (Best-effort — test only asserts no 500 and exactly one Member row.) |
| `display_name_override="🎵"` (1 grapheme emoji) | Accepted. Stored verbatim. |
| `display_name_override` provided on idempotent re-call | Ignored — payload's override is read-only after first join. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_join_group_first_time_returns_201_with_new_member` | New user + existing group → 201; `is_new_member=true`; one fresh Member row. |
| `test_join_group_idempotent_returns_200` | Same user re-joins → 200; `is_new_member=false`; same `member_id`. |
| `test_join_group_idempotent_does_not_overwrite_display_name_override` | Pre-existing override `"DJ"`; re-call with `"DJX"` → stored value stays `"DJ"`. |
| `test_join_group_lowercase_code_normalizes` | POST `"k7m2x9pq"` → resolves; member created. |
| `test_join_group_crockford_substitution_works` | POST `"K7M2X9PQ"` and `"K7M2X9P0"` both resolve when one is the canonical code (depending on substitution rules). Verify the rule: code stored is `"K7M2X9PQ"`; user types `"K7M2X9P0"` (no substitution because `0` already canonical) — that's a different code → 404. Test that `"K7M2I9PQ"` typed by the user → normalize → `"K7M211PQ"` → 404 unless we set up the seed code to match. The exact assertion: `normalize("KIMOPQRS") == "K1M0PQRS"`. |
| `test_join_group_unknown_code_returns_404` | Random 8 chars → 404 `group_not_found`. |
| `test_join_group_malformed_code_returns_404_not_422` | `"K7M2"` (4 chars) → 422 (Pydantic length); `"K7M2X9!Q"` (bad char) after normalize → 404. The Pydantic length check fires before the route handler, so the 422 path is unavoidable for length; the bad-char-after-normalize path returns 404. Document both. |
| `test_join_group_writes_member_joined_activity` | After successful new join, exactly one `group_activity` row with `kind="member_joined"`, payload contains `display_name` and `avatar_color`. |
| `test_join_group_updates_last_active_at` | After new join, `group.last_active_at` is within 1 s of now. |
| `test_join_group_idempotent_does_not_update_last_active_at` | Pre-set `last_active_at` to 1 hour ago; idempotent re-join keeps it within ±1s of original. |
| `test_join_group_unauthenticated_returns_401` | No header → 401. |
| `test_join_group_concurrent_first_join_one_member_row` | Two coroutines POST simultaneously; both 2xx; only one Member row. |
| `test_join_group_after_leave_creates_fresh_member_row` | Join → leave (BE-021 if it exists; otherwise simulate via direct DELETE) → rejoin; `member_id` differs from first; `joined_at` is later. |
| `test_join_group_member_out_resolves_display_name_via_coalesce` | User has no override, no display_name, username `"jerome"` → MemberOut.display_name == `"jerome"`. Then patch display_name="🎵 Jerome"; re-join (idempotent) → MemberOut.display_name updates. |

**Manual QA:**

1. As User A, POST `/api/groups` → get an `invite_code`.
2. As User B, POST `/api/groups/join` with that code → 201, see member.
3. Re-POST as User B → 200, same member_id.
4. POST as User B with an obviously bad code (`"AAAAAAAA"`) → 404.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `group.member_joined` | `group_id`, `member_id`, `user_id`, `is_new_member: bool`, `request_id` |
| `group.join_unknown_code` | `attempted_code_hash` (SHA-256 of normalized — to detect brute-force scans without storing raw guesses), `request_id` (WARNING) |

## 8. Out of scope

| Item | Where |
|---|---|
| Rate limiting on join (anti-brute-force) | BACKLOG-010. |
| Display-name uniqueness within a group | Out of v1 per PRD § 8 OQ-3 (deferred). |
| Magic-link / deep-link join | FE-004 + a follow-up universal-link config (BACKLOG-011). |
| Group-leave endpoint | BE-021 follow-up. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. New joins fail (404 / 405 depending on FastAPI's routing). Existing Member rows unaffected. Coordinate with FE-004.
