# Workflow — setlist-picker

How work gets done in this repo. Read this before opening a task, writing an EPIC, or implementing.

## Three artifacts per multi-task wave

1. **`docs/<wave-name>/EPIC.md`** — wave-level coordination. Defines goal, scale targets (especially Tomorrowland-day projections), task order + dependencies, cross-cutting hard rules, Render deploy mechanic, what's explicitly out of scope.

2. **`tasks/<TASK-XXX>.md`** — per-task implementation contract. Follow the template at `tasks/TASK_TEMPLATE.md`. Each task lists exact files to touch, acceptance criteria with verbatim test method names, SQL snippets for non-trivial queries, structured logging events, and rollback notes.

3. **Minimal coordination message** (Dispatch or human runner): "Read `docs/<wave>/EPIC.md` and `tasks/<TASK-XXX>.md`. Execute strictly per spec. Report back per the Definition of Done."

The coordination message MUST NOT duplicate acceptance criteria, hard rules, or report format — those live in the EPIC and task files. If the implementation session restarts mid-wave, both files are committed; the new session reads them and continues.

## When to skip the EPIC

- Single-task fix (1-2 files, mechanical) — per-task file is enough
- Hot bug fix during incident — single direct prompt
- 3+ related tasks with dependencies or shared "why" — EPIC.md is mandatory

## Branch strategy (v1 phase — pre-launch)

- **`design/initial-schema`** is the v1 integration branch. All v1 work goes here directly OR via per-task feature branches that fast-forward merge back into `design/initial-schema`.
- For parallel implementation by multiple sessions: each spawns a per-task feature branch (e.g., `feat/<task-name>`). Each merges back via `git merge --ff-only` after acceptance.
- No sub-PRs to `design/initial-schema` — Dispatch greenlights merges based on task report; no PR review gate during v1.
- Post-launch (when v1 → main): switch to standard feature branches → PR → squash-merge → main.

## Validation gate (per task)

Every task must satisfy these before commit:
- `pytest` green (BE)
- `ruff check .` green (BE) — zero violations
- `mypy --strict` green (BE) — zero errors on 100+ files
- `npm test` green (FE)
- `npx tsc --noEmit` green (FE)
- snake_case wire JSON — Pydantic models match TS types
- No bare `except Exception` in service layer; specific recoverable types only (`httpx.HTTPError`, `sqlalchemy.exc.*`, `TimeoutError`, `OSError`) per `docs/code_review_known_fixes.md`
- Updated `docs/CODEBASE_GUIDE.md` for any new endpoint, model, screen, or hook

## Deploy + smoke (per task touching live behavior)

After push to `design/initial-schema` (or after ff-merge from feature branch):

1. Render auto-deploys on push.
2. If the task includes an Alembic migration: trigger via Render Jobs API (API key at `~/.config/credentials`, owner `FestivalApp`, service `setlist-picker-dev`). Pattern documented at `tasks/TASK-OFFLINE-PICK-QUEUE.md` and prior PERF tickets.
3. Smoke the changed endpoint(s) via curl against `setlist-picker-dev.onrender.com`. Verify structured-log events fire in Render logs.
4. FE smoke: reload Expo Go on dev device; verify the UI change renders against the deployed BE.

## Festival-day scaling constraints

Setlist is write-heavy and offline-tolerant. Performance work must consider:
- Tomorrowland projection: ~10K concurrent users, 833 picks/sec sustained, 1K picks/sec burst at set-start times
- Spotty cell coverage → offline queue + reconnect drain is the most common path
- LWW conflict resolution via `Pick.state_clock_ms` (DB-enforced — see `docs/perf-wave/EPIC.md`)
- DB connection pool is the architectural ceiling — see `services/api/app/db/session.py`

When designing endpoints or schemas, factor these in.

## What this workflow gives you

- Self-contained task = implementer never needs to ask "what file?" mid-execution
- EPIC = coordinator never has to re-derive wave-level context
- Pre-launch direct-merge model = fast iteration without PR ceremony

## Examples to read

- `tasks/TASK_TEMPLATE.md` — the per-task structure
- `tasks/TASK-OFFLINE-PICK-QUEUE.md` — a worked task spec with verified file paths
- `docs/perf-wave/EPIC.md` — a worked wave EPIC
- `docs/code_review_template.md` — review framing post-v1
- `docs/code_review_known_fixes.md` — recurring trap catalogue

## Memory companion

For Anthropic / Claude agents: workflow is codified in `feedback_epic_ticket_workflow`. Repo rules here are authoritative.
