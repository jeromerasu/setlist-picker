# TASK-SETLIST-PERF-COUNT-SQL — going_count in SQL not Python

## Status

- [x] Ready

## Owner
TBD on pickup.

## Repo + branch

**Repo:** `setlist-picker`
**Branch:** `feat/perf-count-sql-aggregation` off `design/initial-schema`

## Dependencies

None. Can ship in parallel with `TASK-PERF-CONFIG` and `TASK-PERF-BATCH-UPSERT`.

## Scope

In the group-aggregated schedule endpoint (`GET /api/groups/{code}/schedule?day_label=`), the `going_count` and `maybe_count` per set are currently computed by Python iteration over rows returned from the pick + set + stage + member JOIN. Move that aggregation into SQL via `COUNT()` + `GROUP BY` so Postgres does the work and Python receives pre-aggregated counts. Reduces Python CPU under load and removes an O(N) per-request operation. Out of scope: any change to the response shape, the auth flow, the LWW logic, the FE.

## Files to touch

| File | Purpose |
|---|---|
| `services/api/app/services/group_service.py` (verify exact path via grep `get_group_schedule`) | Rewrite the schedule query to use SQL `COUNT(...) FILTER (WHERE state = 'going') AS going_count, COUNT(...) FILTER (WHERE state = 'maybe') AS maybe_count` with `GROUP BY set.id`. Add LEFT JOIN to ensure sets with zero picks still appear. |
| `services/api/tests/test_group_schedule.py` (existing) | Update tests to assert `going_count` field is populated correctly from SQL; add edge-case test for zero-pick set. |
| `docs/CODEBASE_GUIDE.md` | One-line update. |

## Acceptance criteria

- [ ] `GET /api/groups/{code}/schedule?day_label=Day 2` response shape UNCHANGED (`going_count`, `maybe_count`, `member_picks` array still present per set).
- [ ] Sets with zero picks STILL appear in the response with `going_count: 0, maybe_count: 0` (LEFT JOIN guarantee).
- [ ] The schedule query executes EXACTLY 1 SQL statement against the DB per request (verify via SQL log spy). The current per-Python-row loop should not survive.
- [ ] `member_picks` array still includes individual member states (this part stays as a separate JSON aggregation OR is built from the joined rows, but the going_count specifically is pre-aggregated).
- [ ] `pytest`, `ruff check`, `mypy --strict` green.
- [ ] `docs/CODEBASE_GUIDE.md` updated.

## Tests required

- `tests/test_group_schedule.py::test_going_count_aggregated_from_sql`
- `tests/test_group_schedule.py::test_zero_pick_sets_still_appear_with_zero_counts`
- `tests/test_group_schedule.py::test_response_shape_unchanged_member_picks_present`
- `tests/test_group_schedule.py::test_one_statement_per_request`

## Hard rules

- snake_case JSON unchanged.
- LEFT JOIN on pick table required — DON'T use INNER JOIN, would drop zero-pick sets.
- `COUNT(...) FILTER (WHERE ...)` is Postgres-specific syntax. Tests must run under Testcontainers Postgres (not SQLite). Verify the test infrastructure handles this.
- Structured logging: `event=group.schedule.computed entity_id={group_code} day_label={...} set_count={n} statement_count=1`.
- No bare `except Exception` in service code.

## Effort estimate

`S` — ≤½ day. SQL refactor + tests.

## Risk

**Low.** Pure read endpoint, additive SQL change, response shape preserved by tests. Rollback is reverting the query.

## Notes

- The `member_picks` array per set still needs each member's `(user_id, display_name, state)`. Two options:
  - **Option A:** Single query with `array_agg(json_build_object('user_id', user_id, 'display_name', display_name, 'state', state))` — pure SQL, one statement total.
  - **Option B:** First query: per-set going_count + maybe_count via COUNT+GROUP BY. Second query: pull member picks for the relevant sets. Two queries instead of N.
  
  Option A is the cleanest single-statement implementation. Option B is acceptable if the JSON-aggregation syntax adds complexity. Pick A unless it's awkward.

- Verify the existing index on `pick(set_id)` is sufficient for GROUP BY scan. If a compound `(set_id, state)` index helps, propose it as a follow-up — DON'T add it in this ticket.

## Definition of done

- [ ] All acceptance criteria checked.
- [ ] All 4 tests green.
- [ ] Feature branch pushed + fast-forward merged into `design/initial-schema`.
- [ ] Render auto-deploys; smoke `curl /api/groups/<test-code>/schedule?day_label=Day 1` → 200 with going_count populated.
- [ ] `docs/CODEBASE_GUIDE.md` updated.
- [ ] Report posted to Dispatch with commit SHA + sample response.
