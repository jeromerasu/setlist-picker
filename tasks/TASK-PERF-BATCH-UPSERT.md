# TASK-SETLIST-PERF-BATCH-UPSERT — Single SQL statement for /picks/sync

## Status

- [x] Ready

## Owner
TBD on pickup.

## Repo + branch

**Repo:** `setlist-picker`
**Branch:** `feat/perf-batch-upsert-picks-sync` off `design/initial-schema`

## Dependencies

None. Can ship in parallel with `TASK-PERF-CONFIG` and `TASK-PERF-COUNT-SQL`.

## Scope

Replace the per-pick loop in `POST /api/groups/{code}/picks/sync` with a single `INSERT ... ON CONFLICT DO UPDATE` SQL statement covering the entire array. 50 queued picks goes from 250 SQL statements to 1, freeing the DB connection ~5x faster on offline queue drain. The biggest predictable failure mode (connection saturation when multiple users reconnect simultaneously) goes away.

LWW semantics preserved verbatim: `ON CONFLICT (member_id, set_id) DO UPDATE SET state = excluded.state, state_clock_ms = excluded.state_clock_ms WHERE Pick.state_clock_ms < excluded.state_clock_ms` — replays with stale clock are no-ops, identical to the current behavior.

Out of scope: any change to single-pick endpoint `POST /api/groups/{code}/picks` (still one statement, no change needed); any change to the LWW semantics; any change to the `state_clock_ms` clock-skew tolerance; any change to the response shape.

## Files to touch

| File | Purpose |
|---|---|
| `services/api/app/services/group_picks_service.py` (verify exact path with grep `picks/sync`) | Replace per-pick loop with single `INSERT ... ON CONFLICT` using SQLAlchemy `insert(...).on_conflict_do_update(...)` from `sqlalchemy.dialects.postgresql.insert`. |
| `services/api/app/routes/groups.py` (verify the sync route) | Verify the route still wraps the call in one transaction; no change needed if already does. |
| `services/api/tests/test_group_picks_sync.py` (existing — verify path) | Update tests to assert query count == 1 regardless of array length; add a 50-pick array test. |
| `docs/CODEBASE_GUIDE.md` | One-line update referencing the batch upsert pattern. |

## Acceptance criteria

- [ ] `POST /api/groups/{code}/picks/sync` with an array of N picks executes EXACTLY 1 SQL statement against the `pick` table (verify via SQL log spy with N = 1, 10, 50).
- [ ] LWW semantics preserved: replaying a sync with all-stale `state_clock_ms` values returns 200 with no DB writes (assert via SQL spy and DB row count unchanged).
- [ ] Mixed sync (some fresh, some stale): the fresh ones update their rows, the stale ones don't. Total statement count still 1.
- [ ] Response shape UNCHANGED — still returns 200 with the same body the current implementation returns.
- [ ] `pytest`, `ruff check`, `mypy --strict` green.
- [ ] `docs/CODEBASE_GUIDE.md` updated.

## Tests required

- `tests/test_group_picks_sync.py::test_batch_of_50_executes_one_statement`
- `tests/test_group_picks_sync.py::test_all_stale_clocks_no_writes`
- `tests/test_group_picks_sync.py::test_mixed_fresh_and_stale_writes_only_fresh`
- `tests/test_group_picks_sync.py::test_single_pick_array_still_works`
- `tests/test_group_picks_sync.py::test_response_shape_unchanged`

## Hard rules

- snake_case JSON unchanged.
- `state_clock_ms` LWW WHERE clause stays exactly: `WHERE Pick.state_clock_ms < excluded.state_clock_ms`. DON'T change the inequality direction or use `<=` (would cause idempotent replay to fire writes).
- No bare `except Exception` in service code. Specific recoverable types only (`sqlalchemy.exc.IntegrityError`, `OperationalError`).
- Structured logging: `event=group.picks.sync entity_id={member_id} batch_size={n} statement_count=1` so we can verify the optimization holds in production.

## Effort estimate

`S` — ≤½ day. SQLAlchemy syntax for bulk upserts plus tests.

## Risk

**Low-medium.** The query is new and could subtly differ from the per-pick loop. The 5 tests above are designed to catch any divergence. Rollback is reverting the service method.

## Notes

- SQLAlchemy bulk insert pattern (PostgreSQL dialect):
  ```python
  from sqlalchemy.dialects.postgresql import insert
  
  stmt = insert(Pick).values([
      {"member_id": p.member_id, "set_id": p.set_id, "state": p.state, "state_clock_ms": p.state_clock_ms}
      for p in picks
  ])
  stmt = stmt.on_conflict_do_update(
      index_elements=["member_id", "set_id"],
      set_={"state": stmt.excluded.state, "state_clock_ms": stmt.excluded.state_clock_ms},
      where=Pick.state_clock_ms < stmt.excluded.state_clock_ms,
  )
  await session.execute(stmt)
  ```
- This is one SQL statement, one round-trip, one row lock per affected row.
- Counting statements in tests: use `event.listen(engine, "before_cursor_execute", ...)` to increment a counter.

## Definition of done

- [ ] All acceptance criteria checked.
- [ ] All 5 tests green.
- [ ] Feature branch pushed + fast-forward merged into `design/initial-schema`.
- [ ] Render auto-deploys; smoke a sync of 5 picks → 200, all reflected in DB.
- [ ] `docs/CODEBASE_GUIDE.md` updated.
- [ ] Report posted to Dispatch with commit SHA + statement-count proof from tests.
