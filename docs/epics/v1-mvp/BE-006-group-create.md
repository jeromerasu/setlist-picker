# BE-006 — `POST /api/groups` — create group + assign 8-char Crockford invite code + auto-create creator's Member row

**Wave:** 1
**Type:** BE
**Blocked by:** BE-003
**Blocks:** FE-102, FE-002, BE-007, BE-008, BE-009, BE-017
**ADR references:** [ADR-006 § 2.2, § 4.11, § 4.22, § 4.25, § 4.27](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

A signed-in user creates a group scoped to a specific Event. Server assigns an 8-character Crockford base32 invite code, creates the Group row, auto-creates a `Member` row for the creator, and logs a `group_activity` row of kind `group_created`. The FE consumes the response immediately to show the creator the group-detail screen with their invite code.

## 2. Actual solution

`app/services/group_service.py` exposes `create_group(db, creator: User, name: str | None, event_id: UUID) -> GroupCreateResponse`.

Algorithm:

1. SELECT the Event by `event_id`. If missing → 404 `event_not_found`.
2. Generate an 8-char invite code from the Crockford alphabet (`0123456789ABCDEFGHJKMNPQRSTVWXYZ` — no I, L, O, U). Use `secrets.choice` 8 times. Retry up to 5 attempts if collision; after 5 → 500 `invite_code_collision_unrecoverable` and log `group.invite_code_collision_max_retries` at ERROR.
3. INSERT the Group with `name = payload.name or "Friends 🎵"`, `invite_code`, `event_id`, `created_by_user_id = creator.id`, `last_active_at = now()`.
4. INSERT a Member row `(user_id=creator.id, group_id=group.id)` with `display_name_override=None`. The unique index on `(user_id, group_id)` is harmless here — first row for this pair.
5. INSERT a `group_activity` row of kind `group_created` with `payload={"group_name": group.name, "event_id": str(event.event_id), "event_name": event.name}`.
6. Wrap 3 + 4 + 5 in a single transaction. The `get_db` dep auto-commits on the way out.
7. Return `GroupCreateResponse`.

The Group's `name` field defaults to `"Friends 🎵"` per ADR-006 § 2.2 — implemented in the service layer (not the column default) so the wire-shape contract is explicit.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/group_service.py` | `create_group`, `_generate_invite_code`. |
| `services/api/app/services/activity_service.py` | New file — central writer for `group_activity` rows (used by BE-006, BE-007, BE-015, BE-016, and the eventual leave endpoint). |
| `services/api/app/schemas/groups.py` | Add `GroupCreate`, `GroupCreateResponse` (from `docs/schemas/reference/v1_pydantic.py`). |
| `services/api/app/routes/groups.py` | New file — `POST /api/groups`. |
| `services/api/app/main.py` | Include the groups router. |
| `services/api/app/auth/invite_code.py` | `generate_invite_code()` + `CROCKFORD_ALPHABET` constant + `normalize(code: str) -> str` (used by BE-007). |
| `services/api/tests/test_group_create.py` | See § 7. |
| `services/api/tests/test_invite_code.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add `/api/groups` POST. |

## 4. Method signatures / new APIs

```python
# app/schemas/groups.py
class GroupCreate(_Model):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    event_id: UUID


class GroupCreateResponse(_Model):
    group_id: UUID
    name: str
    invite_code: str = Field(min_length=8, max_length=8)
    event_id: UUID
    created_by_user_id: UUID
    created_at: datetime
    member_id: UUID
```

```python
# app/services/group_service.py
async def create_group(
    db: AsyncSession,
    creator: User,
    name: str | None,
    event_id: UUID,
) -> GroupCreateResponse: ...
```

```python
# app/auth/invite_code.py
CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def generate_invite_code() -> str:
    """Returns 8 chars from CROCKFORD_ALPHABET."""


def normalize(raw: str) -> str:
    """Uppercase + I→1, L→1, O→0 mapping. Caller validates length elsewhere."""
```

```python
# app/services/activity_service.py
async def log_activity(
    db: AsyncSession,
    *,
    group_id: UUID,
    member_id: UUID | None,
    kind: ActivityKind,
    payload: dict[str, object],
) -> None: ...
```

Endpoint:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `POST` | `/api/groups` | `GroupCreate` | `GroupCreateResponse` | 201 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 404 | `event_not_found` | `event_id` doesn't exist. |
| 422 | (Pydantic) | `name` length / charset. |
| 500 | `invite_code_collision_unrecoverable` | 5 collision retries failed. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Crockford alphabet | `0123456789ABCDEFGHJKMNPQRSTVWXYZ` | ADR-006 § 4.22. |
| Invite-code length | 8 | ADR-006 § 4.22. |
| Collision retry budget | 5 | At 32^8 ≈ 1.1T codes vs ≤500 active groups (PRD § 2 success metric), collision probability per attempt is ≈ 4.6e-10. Five retries makes failure operationally impossible; the 500 path is a "should never happen" guard. |
| Default group name | `"Friends 🎵"` | ADR-006 § 2.2. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Caller is authenticated but the User row was deleted between token decode and service call | 401 `invalid_token` (BE-003's dependency catches it first). |
| `event_id` is well-formed UUID but no Event exists | 404 `event_not_found`. |
| `event_id` is malformed UUID | 422 Pydantic. |
| `name=""` | 422 — `min_length=1`. |
| `name="   "` | Server strips leading/trailing whitespace per ADR-006 § 4.21; if the result is empty, returns 422 `name_blank`. (Pydantic validator.) |
| `name=None` (omitted) | Defaults to `"Friends 🎵"`. Returned as such. |
| Invite-code collision on attempt 1 | Service retries with a fresh code; succeeds; the duplicate is never visible to the caller. |
| Invite-code collision on attempt 5+ | 500 `invite_code_collision_unrecoverable`. (Test asserts via a monkeypatch that hardcodes the alphabet to one char, forcing collisions.) |
| Creator already has the maximum number of groups | No limit in v1 — the test confirms this. |
| Concurrent creation of two groups by the same user | Both succeed with distinct invite codes; two `group_created` activity rows. |
| Concurrent creation of two groups for the same event | Both succeed — a User can be in many groups for one event in principle; no `(user_id, event_id)` uniqueness. Future v2 if this proves to be a footgun. |
| Apple/Google user with NULL username creates a group | Works; Member row's `display_name_override=None`; render-time COALESCE falls through to `user.display_name`, then `user.username`. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `tests/test_invite_code.py` | `test_generate_invite_code_length_is_8` | Loop 1000 times; every code is exactly 8 chars. |
| `tests/test_invite_code.py` | `test_generate_invite_code_chars_only_in_crockford_alphabet` | Every char appears in `CROCKFORD_ALPHABET`. |
| `tests/test_invite_code.py` | `test_generate_invite_code_distribution` | Over 10k samples, no single char appears > 5σ above expected frequency (sanity check on `secrets.choice`). |
| `tests/test_invite_code.py` | `test_normalize_lowercase_i_maps_to_1` | `normalize("ilo") == "110"`. |
| `tests/test_invite_code.py` | `test_normalize_uppercase_passthrough` | `normalize("AB7K") == "AB7K"`. |
| `tests/test_group_create.py` | `test_create_group_returns_201_with_full_payload` | Auth'd POST → 201; body has `group_id`, `invite_code` (8 chars), `member_id`, `created_at`. |
| `tests/test_group_create.py` | `test_create_group_default_name_when_omitted` | `name` not in body → response `name == "Friends 🎵"`. |
| `tests/test_group_create.py` | `test_create_group_uses_provided_name_after_strip` | `name="  ravers "` → stored + returned `"ravers"`. |
| `tests/test_group_create.py` | `test_create_group_blank_name_returns_422` | `name="   "` → 422 `name_blank`. |
| `tests/test_group_create.py` | `test_create_group_missing_event_returns_404` | random UUID → 404 `event_not_found`. |
| `tests/test_group_create.py` | `test_create_group_auto_creates_member_row` | After POST, SELECT member WHERE user_id=creator AND group_id=new shows one row; response's `member_id` matches. |
| `tests/test_group_create.py` | `test_create_group_logs_group_created_activity` | One `group_activity` row exists with `kind="group_created"` and payload contains `group_name`, `event_id`, `event_name`. |
| `tests/test_group_create.py` | `test_create_group_unauthenticated_returns_401` | No `Authorization` → 401. |
| `tests/test_group_create.py` | `test_create_group_collision_retries_then_succeeds` | Monkeypatch `secrets.choice` to return a fixed char on calls 1–8 (forcing collision on attempt 1), random on calls 9+. Assert the call eventually succeeds, two-row state is consistent. |
| `tests/test_group_create.py` | `test_create_group_collision_max_retries_returns_500` | Monkeypatch to always collide → 500 `invite_code_collision_unrecoverable`; log line emitted. |
| `tests/test_group_create.py` | `test_create_group_atomic_on_member_failure` | Monkeypatch the Member INSERT to raise; assert the Group row is also rolled back. |

**Manual QA:**

1. Auth as a fresh user; POST `/api/groups` with `{"event_id": "<existing event uuid>"}`.
2. Read the response: `invite_code` matches `^[0-9A-HJKMNP-TV-Z]{8}$`.
3. `psql ... -c "select * from group"` shows the row.
4. `psql ... -c "select * from member"` shows the auto-created Member.
5. `psql ... -c "select * from group_activity"` shows the `group_created` row.

**Structured-log lines on success:**

| Event | Fields |
|---|---|
| `group.created` | `group_id`, `invite_code`, `event_id`, `created_by_user_id`, `request_id` |

**On failure:**

| Event | Fields |
|---|---|
| `group.invite_code_collision_retry` | `attempt: int`, `request_id` (INFO; expected to be rare) |
| `group.invite_code_collision_max_retries` | `request_id` (ERROR) |
| `group.event_not_found` | `event_id`, `request_id` (WARNING) |

## 8. Out of scope

| Item | Where |
|---|---|
| `PATCH /api/groups/{invite_code}` rename | Wave 3 — bundled with FE-005 if needed; otherwise BE-018-rename (not currently scheduled, BACKLOG-009). |
| `POST /api/groups/{invite_code}/leave` (hard delete) | BE-021 (post-MVP) — FE-009 gates the call behind a confirmation dialog per ADR-006 § 4.28. EPIC notes this as v1 must-have; add the ticket if FE-009 needs it. |
| Group archival sweep cron | v1.x. |
| Multi-event groups | Permanently out per ADR-006 § 4.25. |
| Inviting via share-sheet | FE-005. |

Note: a "leave group" backend ticket should be added if FE-009 surfaces the action. The ADR-006 § 4.28 acceptance criterion (FE confirmation dialog) is FE-009's responsibility; the corresponding BE endpoint is a small follow-up.

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. Existing Group rows persist; no one can create new ones until revert is undone. FE-002 will show a 404 or 405 to anyone trying to create — acceptable for pre-launch.
