# BE-014 — Pick payload denormalization on `GET /api/groups/{invite_code}`

**Wave:** 2
**Type:** BE
**Blocked by:** BE-009
**Blocks:** FE-006, FE-008
**ADR references:** [ADR-006 § 3.1 Q1, § 4.5, § 4.6](../../decisions/ADR-006-initial-data-schema.md)

## 1. Problem statement

BE-009 returns the group's `members` and event summary but with `picks: []`. This ticket fills in the picks half of `GroupStateResponse` — every Member's picks (active AND tombstoned) keyed by `(member_id, set_id)`, so the FE can reconcile its local expo-sqlite queue.

## 2. Actual solution

Add `_load_picks(db, group_id) -> list[PickSummary]` to `app/services/group_service.py`. Implementation runs Q1 from ADR-006 § 3.1, modified to include tombstoned picks (`AND p.state IN ('active', 'tombstoned')`, no filter).

Reconciliation rationale: ADR-006 § 4.5/4.6 specify LWW on `state_clock_ms`; the FE's expo-sqlite queue may hold pending toggles. To reconcile, the FE needs to see the server's authoritative state for each `(member, set)` pair — including tombstoned states. If we hide tombstones, the FE can't tell "server agrees with my unpick" from "server hasn't heard about my unpick yet."

Wire impact: `GroupStateResponse.picks` becomes `list[PickSummary]` populated with every row keyed `(member_id, set_id)` from the group's members. Caller's own picks AND every other member's picks.

The `Last-Modified` calculation in BE-009 already considers `pick.server_last_updated_at`, so adding picks here doesn't change the 304 behavior.

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/app/services/group_service.py` | Add `_load_picks`. Wire into `get_group_state`. |
| `services/api/app/schemas/groups.py` | (Already has `PickSummary` from BE-009; no changes.) |
| `services/api/tests/test_group_state.py` | Add 6 more tests covering the picks half. |
| `docs/CODEBASE_GUIDE.md` | Update the endpoint description. |

## 4. Method signatures / new APIs

```python
# app/services/group_service.py
async def _load_picks(db: AsyncSession, group_id: UUID) -> list[PickSummary]: ...
```

No new routes; BE-009's endpoint contract evolves.

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Include tombstones? | Yes | FE needs to reconcile its local queue. ADR-006 § 4.5/4.6. |
| Sort order in response | `(member_id, set_id)` | Deterministic — eases FE-side diffing. |
| Max picks per group | No hard cap | At ~10 members × ~100 picks/member, 1000 rows = trivial. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Group with no picks | `picks: []`. |
| Group with only tombstoned picks | Returned with `state="tombstoned"`. |
| Member just joined, no picks yet | Their `member_id` absent from `picks[]`; present in `members[]`. |
| Pick on a Set that was deleted (cascade ran) | Pick already gone via FK CASCADE; doesn't appear. |
| Pick on a Set in a different event | Shouldn't be possible — pick.set_id references a set in this group's event (no FK constraint enforces "same event," but app-layer never creates such a pick). Test asserts there's no such row in valid state. |
| Two members each pick the same set | Both rows present, both `active`. |
| LWW race: client and server have different `state_clock_ms` for the same `(member, set)` | Server's row reflects the LWW-winner. FE reconciles by comparing its local clock to the server's. |

## 7. Acceptable validation

**Tests that MUST exist (added to `tests/test_group_state.py`):**

| Test name | Assertion |
|---|---|
| `test_get_group_state_includes_active_picks` | Seed 2 active picks → both in response with `state="active"`. |
| `test_get_group_state_includes_tombstoned_picks` | Seed 1 tombstoned pick → present with `state="tombstoned"`. |
| `test_get_group_state_picks_sorted_by_member_then_set` | Multiple picks → returned in `(member_id, set_id)` lexical order. |
| `test_get_group_state_picks_include_all_members_not_just_caller` | Member A picks 3 sets, Member B picks 1 → caller as Member C sees all 4 picks. |
| `test_get_group_state_last_modified_reflects_picks` | Pick added → next call's `Last-Modified` advances. |
| `test_get_group_state_picks_excluded_when_member_leaves` | Member leaves (hard delete) → their picks no longer in payload (cascade). |

**Manual QA:**

1. Seed 2 members, 3 picks (1 tombstoned). Curl group state.
2. Verify `picks` length = 3; states = `["active", "active", "tombstoned"]`.

**Structured-log lines:**

| Event | Fields |
|---|---|
| `group.state_picks_loaded` | `group_id`, `pick_count`, `request_id` (DEBUG — merged into the `group.state_200` line from BE-009) |

## 8. Out of scope

| Item | Where |
|---|---|
| Filtering `picks[]` to just active | FE concern — implement client-side. |
| Cursor pagination on picks | Not v1; payload bounded. |

## 9. Structured-log events

(Folded into BE-009's `group.state_200` event with the added `pick_count` field.)

## 10. Rollback plan

Revert. `picks: []` always in `GroupStateResponse`; FE-006 falls back to local cache only. Acceptable for short-term rollback while debugging.
