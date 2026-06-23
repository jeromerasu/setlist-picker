# BE-015 — `POST /api/groups/{invite_code}/picks` + `.../picks/sync` (LWW upsert)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-009
**Blocks:** FE-006
**ADR references:** [ADR-006 § 4.5, § 4.27](../../decisions/ADR-006-initial-data-schema.md), [ADR-004](../../decisions/ADR-004-offline-strategy.md)

## 1. Problem statement

User taps a set on the schedule. The FE writes `state_clock_ms = Date.now()` locally and POSTs the toggle. Server enforces LWW: if incoming `state_clock_ms > existing.state_clock_ms`, accept and persist; otherwise reject (LWW-lost).

`/picks/sync` drains the offline queue from expo-sqlite — same algorithm, batch interface.

## 2. Actual solution

`app/services/pick_service.upsert_pick(db, caller, group, payload: PickCreate) -> PickResult`:

1. Server resolves `member_id` from `(caller.id, group.id)`. Body's `set_id`, `state`, `state_clock_ms` come from payload; **no `member_id` in the body** (ADR-006 § 1.4 — prevents picks-on-behalf-of-another-member).
2. Validate `set_id` belongs to the group's event (`SELECT 1 FROM set WHERE set_id=$1 AND event_id=$2`). If not → 404 `set_not_in_group_event`.
3. Validate `state_clock_ms ≤ now_ms + 1 hour buffer` per EPIC OQ-08 (recommendation B). If not → 400 `pick_clock_skew_rejected` + log.
4. UPSERT: `INSERT ... ON CONFLICT (member_id, set_id) DO UPDATE SET state=excluded.state, state_clock_ms=excluded.state_clock_ms WHERE pick.state_clock_ms < excluded.state_clock_ms`. The `WHERE` makes the update conditional — older clocks lose.
5. SELECT the row back. Compare its `state_clock_ms` to the request's:
   - Equal → server accepted the write. `accepted=True`.
   - Greater → existing row won LWW. `accepted=False`.
   - Less → shouldn't happen (we just updated to ≥).
6. If `accepted=True` AND state transitioned (e.g. NULL→active, active→tombstoned, tombstoned→active), log a `group_activity` row of kind `pick_added` or `pick_removed`.
7. Update `group.last_active_at = now()`.
8. Return `PickResult`.

`/picks/sync` runs `upsert_pick` for each item in the batch (single transaction). Returns `PickSyncResponse(results=[...])`. Failure of one row does **not** abort the batch — each row's `accepted` flag is independent.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/pick_service.py` | New file — `upsert_pick`, `upsert_picks_batch`. |
| `services/api/app/schemas/picks.py` | `PickCreate`, `PickResult`, `PickSyncRequest`, `PickSyncResponse`. |
| `services/api/app/routes/picks.py` | New file — POST single + POST sync. |
| `services/api/app/main.py` | Include picks router (mounted under `/api/groups`). |
| `services/api/app/services/activity_service.py` | Already exists from BE-006; called from pick_service. |
| `services/api/tests/test_picks_create.py` | See § 7. |
| `services/api/tests/test_picks_sync.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoints. |

## 4. Method signatures / new APIs

```python
# app/schemas/picks.py
class PickCreate(_Model):
    set_id: UUID
    state: PickState
    state_clock_ms: int = Field(ge=0)


class PickResult(_Model):
    member_id: UUID
    set_id: UUID
    state: PickState
    state_clock_ms: int
    accepted: bool


class PickSyncRequest(_Model):
    toggles: list[PickCreate] = Field(min_length=1, max_length=500)


class PickSyncResponse(_Model):
    results: list[PickResult]
```

```python
# app/services/pick_service.py
async def upsert_pick(
    db: AsyncSession,
    caller: User,
    group: Group,
    payload: PickCreate,
) -> PickResult: ...


async def upsert_picks_batch(
    db: AsyncSession,
    caller: User,
    group: Group,
    toggles: list[PickCreate],
) -> list[PickResult]: ...
```

Endpoints:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `POST` | `/api/groups/{invite_code}/picks` | `PickCreate` | `PickResult` | 200 |
| `POST` | `/api/groups/{invite_code}/picks/sync` | `PickSyncRequest` | `PickSyncResponse` | 200 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 404 | `group_not_found` | — |
| 403 | `not_a_member` | — |
| 404 | `set_not_in_group_event` | `set_id` references a set in a different event. |
| 400 | `pick_clock_skew_rejected` | `state_clock_ms > now_ms + 3_600_000`. |

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Clock-skew buffer | 3_600_000 ms (1 hour) | EPIC OQ-08 / ADR-006 § 5.3 (B). |
| Batch size limit | 500 toggles | A "festival-long offline session" likely caps at ~100; 5× headroom. Protects against runaway requests. |
| Per-row transaction in batch? | No — single transaction for the batch | Atomic-or-nothing semantics for the FE. But individual rows can be `accepted=False` (LWW-lost) inside the same transaction. |
| `activity` row written? | Only on actual state transition | NULL→active, active→tombstoned, tombstoned→active. No-op (active→active with same state_clock_ms) writes no activity. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| First pick for `(member, set)` | INSERT path; row created; `accepted=True`. Activity logged as `pick_added`. |
| Re-pick (state=active, was already active) | UPSERT updates `state_clock_ms` if newer; no state change → no activity. `accepted=True`. |
| Unpick (state=tombstoned, was active) | UPSERT updates state + clock; activity `pick_removed`. `accepted=True`. |
| Rapid re-pick (state=active, was tombstoned) | Activity `pick_added`. `accepted=True`. |
| LWW-lost (incoming clock < server's) | Row unchanged; `accepted=False`. FE reconciles by re-rendering server state. |
| `state_clock_ms = server_now + 30 minutes` | Within buffer; accepted. |
| `state_clock_ms = server_now + 2 hours` | 400 `pick_clock_skew_rejected`. |
| `set_id` references a Set in a different Event | 404 `set_not_in_group_event`. Defensive — the FE shouldn't send these but a stale lineup payload could. |
| `set_id` for a Set that no longer exists (deleted) | Same — 404. |
| `set_id` malformed UUID | 422 Pydantic. |
| Caller not a Member of the group | 403 `not_a_member`. |
| Batch: 100 toggles, 5 LWW-lost | Response has 100 results, 95 `accepted=True`, 5 `accepted=False`. 200. |
| Batch: 1 toggle has invalid `set_id` | That row's `accepted=False`? No — we treat invalid `set_id` as a hard failure for that row, not LWW. **Choice: skip the row, return `accepted=False` with `state` echoing the request, and log `pick.set_id_not_in_event` at WARNING.** The whole batch still returns 200. Test enforces this. |
| Empty batch | 422 (Pydantic `min_length=1`). |
| Batch with > 500 toggles | 422 (Pydantic `max_length=500`). |
| Concurrent POSTs for the same `(member, set)` from two devices | Postgres serializes via the row-level lock from the UPSERT. Higher clock wins. Activity row writes happen inside the same transaction; conditional. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `tests/test_picks_create.py` | `test_first_pick_creates_row_and_activity` | POST `state="active"`, `state_clock_ms=now_ms`; row exists; `accepted=true`; 1 activity row of kind `pick_added`. |
| `tests/test_picks_create.py` | `test_unpick_writes_tombstoned_state_and_activity` | POST `state="tombstoned"`; row updated; activity `pick_removed`. |
| `tests/test_picks_create.py` | `test_pick_same_state_no_activity_written` | POST active twice with monotonic clock — second has same `state` but newer clock; only one activity row exists. |
| `tests/test_picks_create.py` | `test_lww_loss_returns_accepted_false` | Pre-seed row with clock=2000; POST clock=1000; `accepted=false`; DB row unchanged. |
| `tests/test_picks_create.py` | `test_clock_skew_beyond_buffer_returns_400` | clock=`server_now_ms + 2h` → 400 `pick_clock_skew_rejected`. |
| `tests/test_picks_create.py` | `test_set_in_different_event_returns_404` | Pick a set whose event ≠ group's event → 404 `set_not_in_group_event`. |
| `tests/test_picks_create.py` | `test_not_a_member_returns_403` | Auth'd user but not a Member → 403. |
| `tests/test_picks_create.py` | `test_member_id_not_in_body_is_inferred` | POST body lacks `member_id`; server inferred member matches caller; another user POSTing the same set creates their own pick (different `member_id`). |
| `tests/test_picks_create.py` | `test_group_last_active_at_updated` | After a successful POST, `group.last_active_at` ≈ now. |
| `tests/test_picks_create.py` | `test_concurrent_pick_higher_clock_wins` | Two concurrent POSTs for the same set: clock=1000 and clock=2000; final state has clock=2000; both responses succeed but only the higher-clock one has `accepted=true`. |
| `tests/test_picks_sync.py` | `test_sync_processes_all_toggles_in_one_transaction` | Batch of 3 toggles, all valid → all 3 written, 1 activity per state transition. |
| `tests/test_picks_sync.py` | `test_sync_mixed_lww_results_returns_200_with_per_row_status` | Batch of 4 toggles, 2 lose LWW → response has 4 results; 2 `accepted=true`, 2 `accepted=false`. |
| `tests/test_picks_sync.py` | `test_sync_invalid_set_id_skips_row_logs_warning` | Batch contains 1 toggle with bad `set_id` → that row's `accepted=false`; log line `pick.set_id_not_in_event`; other rows succeed. |
| `tests/test_picks_sync.py` | `test_sync_empty_batch_returns_422` | `toggles=[]` → 422. |
| `tests/test_picks_sync.py` | `test_sync_batch_too_large_returns_422` | 501 toggles → 422. |

**Manual QA:**

1. POST a pick; GET group state; pick appears in `picks[]`.
2. POST same pick with older `state_clock_ms` → `accepted=false`; state unchanged.
3. Post a batch of 5 via `/picks/sync`; all reflected.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `pick.upserted` | `group_id`, `member_id`, `set_id`, `state`, `state_clock_ms`, `accepted`, `request_id` |
| `pick.clock_skew_rejected` | `group_id`, `member_id`, `set_id`, `incoming_clock_ms`, `server_clock_ms`, `request_id` (WARNING) |
| `pick.set_id_not_in_event` | `group_id`, `set_id`, `request_id` (WARNING — defensive) |

## 8. Out of scope

| Item | Where |
|---|---|
| Conflict warning (overlapping picks) | FE-side per calendar-spec FE-CAL-006. |
| Push notification on pick | v1.x. |
| `state="maybe"` (prototype tri-state) | Permanently out — handled FE-only per EPIC § 8. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. New picks fail; existing picks unaffected. Activity table doesn't get new pick rows. FE-006 will show its local optimistic state but POSTs will 404/405; user sees a sync error toast.
