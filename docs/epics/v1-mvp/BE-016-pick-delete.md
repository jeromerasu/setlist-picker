# BE-016 — `DELETE /api/groups/{invite_code}/picks/{set_id}` (tombstone unpick)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-015
**Blocks:** FE-006
**ADR references:** [ADR-006 § 4.5, § 4.6](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

Explicit unpick. Conceptually a wrapper for "POST with state=tombstoned" but the FE may use the verb `DELETE` to signal intent. The body still carries `state_clock_ms` so LWW applies.

## 2. Actual solution

`app/routes/picks.py` adds:

```
DELETE /api/groups/{invite_code}/picks/{set_id}
Body: PickRemoveRequest { state_clock_ms: int }
```

The handler builds a `PickCreate(set_id=set_id, state="tombstoned", state_clock_ms=body.state_clock_ms)` and delegates to `pick_service.upsert_pick`. Returns `PickResult`.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/routes/picks.py` | Add DELETE route. |
| `services/api/app/schemas/picks.py` | Add `PickRemoveRequest`. |
| `services/api/tests/test_picks_delete.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoint. |

## 4. Method signatures / new APIs

```python
class PickRemoveRequest(_Model):
    state_clock_ms: int = Field(ge=0)
```

Endpoint:

| Method | Path | Body | Response | Status |
|---|---|---|---|---|
| `DELETE` | `/api/groups/{invite_code}/picks/{set_id}` | `PickRemoveRequest` | `PickResult` | 200 |

Errors mirror BE-015.

## 5. Constants and thresholds

Same as BE-015.

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Unpick a set the user never picked | Creates a tombstone row with `state="tombstoned"`. No activity logged (no state transition from `active`). |
| Unpick a set whose row is already tombstoned with higher clock | LWW-lost; `accepted=false`. |
| Unpick with clock in the future | Same `pick_clock_skew_rejected`. |
| Concurrent DELETE + POST(active) for same set | LWW resolves on `state_clock_ms`. |

## 7. Acceptable validation

**Tests that MUST exist:**

| Test name | Assertion |
|---|---|
| `test_delete_pick_tombstones_active_row` | Pre-seed `state="active"`, clock=1000; DELETE with clock=2000 → row state="tombstoned" with clock=2000; activity `pick_removed`. |
| `test_delete_pick_never_picked_creates_tombstone_no_activity` | No prior row; DELETE → row created with state="tombstoned"; no activity row. |
| `test_delete_pick_lww_lost_returns_accepted_false` | Pre-seed tombstoned clock=2000; DELETE clock=1000 → `accepted=false`. |
| `test_delete_pick_clock_skew_returns_400` | Clock 2h in future → 400. |
| `test_delete_pick_set_id_not_in_event_returns_404` | 404 `set_not_in_group_event`. |
| `test_delete_pick_not_a_member_returns_403` | 403 `not_a_member`. |

**Manual QA:**

1. POST a pick; DELETE it; GET group state → row state="tombstoned".

**Structured-log lines:** (Same as BE-015 — `pick.upserted` with `state="tombstoned"`.)

## 8. Out of scope

| Item | Where |
|---|---|
| Physical row delete | Not in v1 — tombstone preserves LWW correctness per ADR-006 § 4.6. |
| Bulk DELETE | Use `/picks/sync` with `state="tombstoned"` rows. |

## 9. Structured-log events

(Inherits from BE-015.)

## 10. Rollback plan

Revert. Users can still unpick via `POST /picks` with `state="tombstoned"` — FE may need to call that path as fallback. Test before rollback.
