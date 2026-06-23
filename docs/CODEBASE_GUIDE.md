# Codebase Guide — setlist-picker

This guide stays current as code lands. Every PR that adds, removes, or renames a module / class / endpoint MUST update this file (per [CLAUDE.md](../CLAUDE.md) hard rules). It's the orientation map for new contributors and AI sessions — keep it terse, file-by-file, no prose paragraphs inside the package tables.

## Architecture

| Surface | Language / Framework | Notes |
|---|---|---|
| Web client | TypeScript + Next.js (App Router) + PWA | `apps/web/` |
| Backend API | Python 3.12 + FastAPI + SQLAlchemy 2.0 async + Pydantic v2 | `services/api/` |
| Shared types | TypeScript types generated from OpenAPI | `packages/types/` |
| Datastore | Postgres 16 (asyncpg); Alembic migrations | `services/api/alembic/` |
| Build orchestration | Turborepo for TS apps + packages; `uv` for Python service | `turbo.json`, `services/api/pyproject.toml` |

## Data model + auth

The v1 data schema (users, groups, members, events, stages, sets, artists, picks, artist_cache) AND the auth model (JWT-based with username + password) are specified in [decisions/ADR-006-initial-data-schema.md](decisions/ADR-006-initial-data-schema.md). ADR-006 supersedes [ADR-003](decisions/ADR-003-auth-model.md) (anonymous group-code access). The Pydantic wire-shape reference for every v1 endpoint — including the auth flows — lives at [schemas/reference/v1_pydantic.py](schemas/reference/v1_pydantic.py); it's a design artifact, not yet wired into `services/api/`. Every PR that adds or renames a column or endpoint MUST update ADR-006 (or supersede it with ADR-NNN) and the Pydantic reference.

## Backend entry points

| File | Purpose |
|---|---|
| `services/api/app/main.py` | `create_app()` factory + module-level `app` export |
| `services/api/app/routes/health.py` | `GET /healthz` — liveness probe |
| `services/api/app/routes/auth.py` | `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/refresh` |
| `services/api/app/routes/users.py` | `GET /api/users/me`, `PATCH /api/users/me` |

## `services/api/`

### `services/api/app/`

| File | Purpose |
|---|---|
| `app/__init__.py` | Package marker |
| `app/main.py` | `create_app(settings?)` — FastAPI factory with lifespan logging |
| `app/config.py` | `Settings(BaseSettings)` — env-var loader (pydantic-settings) |
| `app/logging.py` | `configure_logging(level)` — installs structlog JSON renderer |

### `services/api/app/routes/`

| File | Purpose |
|---|---|
| `routes/__init__.py` | Package marker |
| `routes/health.py` | `GET /healthz` → `{"status":"ok","service":"setlist-picker-api"}` |
| `routes/auth.py` | Signup, login, token refresh endpoints |
| `routes/users.py` | `GET /PATCH /api/users/me` — authenticated user profile |

### `services/api/app/db/`

| File | Purpose |
|---|---|
| `db/__init__.py` | Re-exports `Base`, `async_session_maker`, `get_db` |
| `db/base.py` | `Base(DeclarativeBase)` + `TIMESTAMPTZ` type alias |
| `db/uuid7.py` | `uuid7() -> uuid.UUID` wrapper around `uuid_utils.uuid7()` |
| `db/session.py` | Lazy-init `AsyncEngine`, `get_session_maker()`, `get_db()` FastAPI dep |
| `db/models/user.py` | `User` ORM model (ADR-006 § 2.1) |
| `db/models/event.py` | `Event` ORM model (§ 2.4) |
| `db/models/group.py` | `Group` ORM model (§ 2.2) |
| `db/models/member.py` | `Member` ORM model (§ 2.3) |
| `db/models/device.py` | `Device` ORM model (§ 2.12) |
| `db/models/stage.py` | `Stage` ORM model (§ 2.5) |
| `db/models/set_.py` | `Set` ORM model (§ 2.6; named `set_.py` to avoid Python builtin conflict) |
| `db/models/artist.py` | `Artist`, `ArtistSourceRef`, `SetArtist` ORM models (§ 2.7–2.9) |
| `db/models/pick.py` | `Pick` ORM model (§ 2.10) |
| `db/models/artist_cache.py` | `ArtistCache` ORM model (§ 2.11) |
| `db/models/group_activity.py` | `GroupActivity` ORM model (§ 2.13) |

### `services/api/app/auth/`

| File | Purpose |
|---|---|
| `auth/__init__.py` | Re-exports all auth symbols |
| `auth/hashing.py` | `hash_password`, `verify_password`, `dummy_verify` (argon2-cffi; timing-safe) |
| `auth/jwt.py` | `encode_access`, `encode_refresh`, `decode`; `Claims` Pydantic model |
| `auth/palette.py` | `AVATAR_PALETTE` — 12 hex colors for deterministic avatar assignment |
| `auth/dependencies.py` | `current_user` FastAPI dep — decodes Bearer token, loads User, logs rejections |

### `services/api/app/schemas/`

| File | Purpose |
|---|---|
| `schemas/auth.py` | `UserCreate`, `UserLogin`, `TokenPair`, `AuthResponse`, `TokenRefreshRequest`, `AppleSignInRequest`, `GoogleSignInRequest`, `UserOut`, `UserUpdate` |

### `services/api/app/services/`

| File | Purpose |
|---|---|
| `services/user_service.py` | `create_local_user`, `authenticate`, `patch_user` — all use `begin_nested()` for safe IntegrityError handling |

### `services/api/app/middleware/`

| File | Purpose |
|---|---|
| `middleware/request_id.py` | `RequestIdMiddleware` — injects `request_id` UUID into structlog context per request |

### `services/api/alembic/`

| File | Purpose |
|---|---|
| `alembic/env.py` | Async-aware migration runner (`asyncio.run(run_async_migrations())`) |
| `alembic/versions/0001_v001_baseline.py` | V001 hand-written migration: 13 tables + 27 indexes per ADR-006 |

## Schema

The full schema is specified in [ADR-006](decisions/ADR-006-initial-data-schema.md). V001 creates 13 tables: `user`, `event`, `group`, `member`, `device`, `stage`, `set`, `artist`, `artist_source_ref`, `set_artist`, `pick`, `artist_cache`, `group_activity`.

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
