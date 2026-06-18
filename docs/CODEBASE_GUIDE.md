# Codebase Guide — setlist-picker

This guide stays current as code lands. Every PR that adds, removes, or renames a module / class / endpoint MUST update this file (per [CLAUDE.md](../CLAUDE.md) hard rules). It's the orientation map for new contributors and AI sessions — keep it terse, file-by-file, no prose paragraphs inside the package tables.

## Architecture

| Surface | Language / Framework | Notes |
|---|---|---|
| Web client | TypeScript + Next.js (App Router) + PWA | `apps/web/` |
| Backend API | Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 | `services/api/` |
| Shared types | TypeScript types generated from OpenAPI | `packages/types/` |
| Datastore | SQLite (v1); Postgres-ready via SQLAlchemy dialect | `services/api/data/` (gitignored) |
| Build orchestration | Turborepo for TS apps + packages; `uv` for Python service | `turbo.json`, `services/api/pyproject.toml` |

## Data model

The v1 data schema (groups, members, events, stages, sets, artists, picks, artist_cache) is specified in [decisions/ADR-006-initial-data-schema.md](decisions/ADR-006-initial-data-schema.md). The Pydantic wire-shape reference for every v1 endpoint lives at [schemas/reference/v1_pydantic.py](schemas/reference/v1_pydantic.py) — a design artifact, not yet wired into `services/api/`. Every PR that adds or renames a column or endpoint MUST update ADR-006 (or supersede it with ADR-NNN) and the Pydantic reference.

## Backend entry points

(Stub — populates as code lands. Pattern: `File | Purpose`.)

| File | Purpose |
|---|---|
| _(none yet)_ | |

## `services/api/`

Stub. Each `##` package section below holds a `File | Purpose` table per file as code lands.

### `services/api/app/`

(empty)

### `services/api/app/api/`

(empty)

### `services/api/app/models/`

(empty)

### `services/api/app/services/`

(empty)

### `services/api/app/integrations/`

(empty)

### `services/api/alembic/`

(empty)

## `apps/web/`

Stub.

### `apps/web/src/app/`

(empty)

### `apps/web/src/components/`

(empty)

### `apps/web/src/lib/`

(empty)

### `apps/web/src/hooks/`

(empty)

## `packages/types/`

Stub.

| File | Purpose |
|---|---|
| _(none yet)_ | |

## Cross-repo interactions

(N/A — setlist-picker is self-contained. This section will populate if the project ever splits across multiple repos.)

## Invariants

- **snake_case wire JSON.** Backend Pydantic models use snake_case fields (PEP 8). Frontend TypeScript interfaces use snake_case fields to match the wire. ESLint warnings about naming convention are disabled for API types.
- **`'use client'` directive on line 1** for every interactive Next.js component. NF-001 in [code_review_known_fixes.md](code_review_known_fixes.md).
- **No bare `except Exception`** in service-layer code. NF-002 in [code_review_known_fixes.md](code_review_known_fixes.md).
- **Defensive rendering.** Frontend `.map` / `.length` / `.some` against query data must guard for `undefined`. NF-003.
- **No top-level browser-API reads** in SSR-shared code. NF-004.

## How to update this guide

- After your PR is merged, audit the package tables for new files you added.
- New endpoints go in `Backend entry points` AND in the appropriate `app/api/` table.
- New shared types go in `packages/types`.
- New dependencies go in the appropriate package table (`pyproject.toml` for Python, `package.json` for TS).
- Don't bloat purpose cells — 1–2 sentences max.
