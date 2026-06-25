# EPIC — setlist festival-day performance wave

Worked example of the wave-level coordination doc per `docs/WORKFLOW.md`. Other waves should mirror this structure.

## Goal

Make the setlist BE handle Tomorrowland-day write bursts (833 picks/sec sustained, 1K picks/sec peak at set-start) and reconnect-drain bursts (5K concurrent writes when 100 users come back online together) without dropping requests or saturating the DB connection pool. Reads stay fast on festival 4G via gzip + ETag.

## Why now

Tomorrowland Weekend 2 (2026-07-24 → 2026-07-26) is two weeks out. At 400K festival attendance × 2-5% adoption = 8-20K concurrent users at peak. Analysis (read-only investigation, 2026-06-25) found:

- **DB connection pool capped at 20** (`pool_size=5, max_overflow=15`) — pick writes alone need ~21 connections at sustained load. This is the architectural ceiling that breaks first.
- **`/picks/sync` loops one-by-one** — 50 queued picks per user → 250 SQL statements holding one connection for ~2.5s. 20 users reconnecting at once saturates the entire pool. Highest-risk failure mode.
- **No `GzipMiddleware`** — lineup payload is 80-150KB uncompressed → painful on festival 4G.
- **No ETag on `/lineup`** — every refetch re-downloads the full payload.
- **`going_count` aggregated in Python**, not SQL — wastes CPU under load.

What's already well-designed (DON'T touch):
- LWW conflict resolution enforced at DB level via `ON CONFLICT WHERE state_clock_ms < excluded.state_clock_ms` (replays are safely no-ops)
- Group schedule is a single JOIN — no N+1
- HS256 JWT — microseconds to verify
- 304 support on snapshot via `If-Modified-Since` against `group.last_active_at`
- Pick PK `(member_id, set_id)` — no false sharing
- Indexes on hot paths

## What's in the wave (3 tasks)

| # | Task | Effort | Risk | Depends on |
|---|---|---|---|---|
| 1 | [TASK-PERF-CONFIG — Pool + Gzip + ETag](../../tasks/TASK-PERF-CONFIG.md) | XS (≤1 hour) | Low | none |
| 2 | [TASK-PERF-BATCH-UPSERT — Single SQL for /picks/sync](../../tasks/TASK-PERF-BATCH-UPSERT.md) | S (≤½ day) | Low-Medium | none |
| 3 | [TASK-PERF-COUNT-SQL — going_count via SQL](../../tasks/TASK-PERF-COUNT-SQL.md) | S (≤½ day) | Low | none |

All three are independently shippable. Recommended order: CONFIG first (immediate headroom, trivial), then BATCH-UPSERT (the queue-drain failure mode), then COUNT-SQL.

## What's explicitly out of scope (skipped — overengineering for now)

- Redis caching layer — add only when DB CPU sustained >70%
- Read replicas — Render's pool tuning handles current load
- WebSocket / SSE for live updates — polling at 15-30s is fine for v1; WebSocket is a real engineering project, not a sprint task
- Snapshot pre-computation — 304 already works for typical traffic
- Materialized views — summary tables get 90% of the way

## Festival-day projections (the math)

- 10K concurrent users × 5 picks/min average → **833 picks/sec sustained**
- Burst at set-start time (e.g., Charlotte de Witte takes the stage): **1K picks/sec peak**
- Schedule reads: ~33 reads/sec sustained
- Offline queue drains: 50 queued picks × 100 users reconnecting at once → **5K concurrent writes**

After this wave:
- Pool 50 → handles ~10× burst headroom
- `/picks/sync` single statement → 50-pick drain goes from 250 statements to 1 (50× faster connection turnover)
- Gzip → lineup payload drops 60-80%
- ETag → 95% of lineup refetches return 304 (zero bandwidth)
- SQL `COUNT FILTER` → aggregation moves from Python to Postgres (CPU offload)

## Cross-cutting hard rules

These apply to every task in the wave; tasks reference but don't re-state:
- All commits on `design/initial-schema` (v1 integration branch) via per-task feature branches → fast-forward merge
- `pytest && ruff check . && mypy --strict` green at each commit
- No bare `except Exception` in service code; specific recoverable types (`sqlalchemy.exc.IntegrityError`, `httpx.HTTPError`, `OSError`)
- snake_case wire JSON unchanged
- `state_clock_ms` LWW semantics preserved exactly (no inequality direction changes)
- Structured logging: `event=<area>.<action> entity_id=<id> duration_ms=<n> statement_count=<n>` so we can verify optimizations hold in Render logs
- Update `docs/CODEBASE_GUIDE.md` whenever a new pattern or endpoint behavior changes

## Render deploy mechanic (auto-deploy)

`design/initial-schema` push triggers Render auto-deploy on `setlist-picker-dev`. For migrations:

```bash
export RENDER_API_KEY=$(grep -oE 'render_api_key=\S+' ~/.config/credentials | cut -d= -f2)
OWNERS_JSON=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" 'https://api.render.com/v1/owners')
FESTIVALAPP_OWNER_ID=$(echo "$OWNERS_JSON" | jq -r '.[] | select(.owner.name == "FestivalApp") | .owner.id')
SVC=$(curl -s -H "Authorization: Bearer $RENDER_API_KEY" "https://api.render.com/v1/services?ownerId=${FESTIVALAPP_OWNER_ID}&name=setlist-picker-dev&limit=5" | jq -r '.[0].service.id')

# Trigger alembic upgrade (only for tasks with migrations)
JOB=$(curl -s -X POST -H "Authorization: Bearer $RENDER_API_KEY" -H "Content-Type: application/json" \
  -d '{"startCommand": "uv run alembic upgrade head"}' \
  "https://api.render.com/v1/services/$SVC/jobs")
```

None of the 3 PERF tasks include a migration, so this isn't needed for the wave — but the pattern is reused for any future task that does.

## Report-back format (every task)

When a task lands, the implementation session reports back with:
- Final commit SHA on `design/initial-schema` after fast-forward merge
- Test count delta + ruff + mypy results
- Smoke output (curl + headers / response excerpts)
- Statement-count proof (for the SQL-tuning tasks)
- Render deploy status (auto-fires)
- Any deviation from spec called out explicitly

## Expected wave outcome

After all 3 tasks land:
- DB connection headroom for burst load
- `/picks/sync` resilient to reconnect bursts (single statement per call)
- Lineup payload size cut by 60-80%
- Lineup refetches return 304 (zero bandwidth on cache hit)
- `going_count` computed in DB (CPU savings under load)

## Sequencing with the byb perf wave

The byb perf wave lives at `byb/docs/perf-wave/EPIC.md`. Different repos, different deploy targets — sessions run in parallel without collision. Dispatch coordinates which session works which task.

## When to revisit this wave

- After Tomorrowland: measure actual peak load + Render plan utilization. Decide if Redis cache layer is warranted before the next festival event.
- If pool saturation hits despite the 5-50 increase: profile per-request connection holding time + bump to a paid Render plan (more connections supported).
- If pick write latency exceeds 200ms p95 at peak: investigate batch insert via copy_from or further DB scaling.
