# Architecture — setlist-picker

System-level decisions. Reflects locked-in choices from the initial design sessions. Update this when something at the system level changes.

## Stack

### Client (apps/web)

| Layer | Tech |
|---|---|
| Framework | Next.js (App Router) + TypeScript |
| Styling | Tailwind + shadcn/ui (component primitives) |
| State | React Query (server state) + local React state |
| PWA | Service worker (Workbox), Web App Manifest |
| Offline storage | IndexedDB write queue + cached lineup snapshot |
| Build | Turborepo orchestration |

### Backend (services/api)

| Layer | Tech |
|---|---|
| Framework | FastAPI + uvicorn |
| Runtime | Python 3.12+ |
| Package manager | uv |
| DTOs / validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 (async) |
| Migrations | Alembic |
| Testing | pytest + pytest-asyncio + httpx test client |
| Lint / format | Ruff |
| Type check | mypy --strict |

### Datastore

PostgreSQL is the long-term target. For v1 we ship SQLite — easier deploy, no separate DB service, plenty of headroom for the initial scale. SQLAlchemy's dialect abstraction keeps the migration cheap when we need it.

### Hosting

- Backend: Render web service (`services/api`) with a 1 GB persistent disk for the SQLite file.
- Frontend: Render Static Site or Vercel — either works. Static export from Next.js.
- External APIs: Spotify (read-only, backend-side; client credentials grant).

### Monorepo

Single GitHub repo with Turborepo for TypeScript orchestration. Python service lives as a sibling at `services/api` with its own build config (`uv` + `pyproject.toml`). Shared TypeScript types in `packages/types` generated from the OpenAPI schema FastAPI produces.

See [ADR-002](decisions/ADR-002-monorepo-structure.md).

## Data model

Ten tables at v1: `group`, `member`, `event`, `stage`, `set`, `artist`, `artist_source_ref`, `set_artist`, `pick`, `artist_cache`. The group is anonymous (8-char Crockford base32 PK); members and content entities use UUIDv7; picks tombstone on unpick with a client-assigned `state_clock_ms` for last-write-wins reconciliation; artists are deduplicated globally on `name_normalized`; the cache lives independently of the artist registry.

**The authoritative schema spec — every column, FK, index, design decision, and open question — is [ADR-006: Initial data schema](decisions/ADR-006-initial-data-schema.md).** The Pydantic wire-shape reference for every v1 endpoint is at [docs/schemas/reference/v1_pydantic.py](schemas/reference/v1_pydantic.py).

## Auth model

ADR-006 supersedes ADR-003: v1 ships authenticated user accounts (username + password + JWT). See [ADR-006 § 1 Auth model](decisions/ADR-006-initial-data-schema.md). HS256-signed access tokens (24h) + refresh tokens (7d); secret in `JWT_SECRET` env var. Every endpoint outside `/auth/*` requires `Authorization: Bearer <access_token>`. Group-scoped endpoints additionally verify the caller is an active Member of the group identified by `invite_code`.

## API surface (v1, planned)

Public (no auth required):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/auth/signup` | POST | Create user; returns user + JWT pair. |
| `/api/auth/login` | POST | Username + password → JWT pair. Username comparison `LOWER() = LOWER()`. |
| `/api/auth/refresh` | POST | Exchange refresh token for a new access + refresh pair. |

Authenticated (Bearer token required):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/users/me` | GET | Current user. |
| `/api/users/me` | PATCH | Update display name / avatar color / email. |
| `/api/users/me/groups` | GET | All groups the user is a Member of. |
| `/api/groups` | POST | Create a group; returns group + `invite_code`. Creator becomes a Member. |
| `/api/groups/join` | POST | Join via `{invite_code, display_name_override?}`. Idempotent — rejoin re-activates. |
| `/api/groups/{invite_code}` | GET | Group state (members, picks). Polled every 15s; supports `If-Modified-Since` → 304. |
| `/api/groups/{invite_code}` | PATCH | Rename the group. |
| `/api/groups/{invite_code}/leave` | POST | Soft-leave the current user from the group. |
| `/api/groups/{invite_code}/picks` | POST | Add or upsert a pick. Server runs LWW per ADR-006 § 4.5. `member_id` derived server-side from `(current_user, group)`. |
| `/api/groups/{invite_code}/picks/sync` | POST | Bulk drain of the offline IndexedDB queue. |
| `/api/groups/{invite_code}/picks/{set_id}` | DELETE | Remove (tombstone) a pick. |
| `/api/groups/{invite_code}/snapshot` | GET | Screenshotable "where will we be at time T" view; per-stage sets in `[at, at + window_minutes]` with **all members'** picks + display names + avatar colors denormalized. ADR-006 § 4.13. |
| `/api/events` | GET | List events (one-per-deploy in v1). |
| `/api/events/{event_id}/lineup` | GET | Full lineup (stages + days + sets). |
| `/api/events/import` | POST | Admin import (paste lineup JSON). Admin-token-gated; not JWT-gated. |
| `/api/artists/{artist_name}` | GET | Artist drill-down data — backed by `artist_cache`. |

All responses are JSON, snake_case. See [CLAUDE.md](../CLAUDE.md) for the wire-format convention.

## Real-time strategy

v1: polling with conditional GETs (per ADR-006 § 4.14). The frontend polls `GET /api/groups/{invite_code}` every 15s while the calendar view is foregrounded, 30s while the snapshot view is open. The server returns a `Last-Modified` header derived from `MAX(pick.server_last_updated_at, member.joined_at, member.left_at)` for the group; the FE sends `If-Modified-Since` and the server returns **304 Not Modified** when nothing changed. Most polls during quiet periods will hit 304 — cheap on metered mobile data.

v2: WebSockets if user reports indicate the polling delay hurts the "who's where right now" feel during the event. Not anticipated for v1.

## Offline strategy

See [ADR-004](decisions/ADR-004-offline-strategy.md) for the full rationale.

- Service worker registers on first load.
- Cache-first for the lineup JSON, fonts, JS/CSS bundles.
- Network-first with stale-while-revalidate for group state.
- IndexedDB queue for offline mutations: `{action: 'add_pick' | 'remove_pick', payload, queued_at}`.
- On reconnect: process queue oldest-first against the API. Last-write-wins on conflicts (the API's `picked_at` and `removed_at` settle the order).
- UI shows an "Offline — changes will sync" badge when the network is down.
- Stale-warning if group state hasn't refetched in over 4 hours.

## External integrations

### Spotify

Backend-only. Client credentials flow — no user OAuth. The backend stores the client ID + client secret in `services/api/.env`; the frontend never sees either.

- Endpoints used: search artists by name, get artist details (genres, images), get top tracks.
- Spotify's `related-artists` endpoint was deprecated in late 2024. Fallback chain captured in [ADR-005](decisions/ADR-005-music-data-source.md): try Last.fm `getsimilar`, then a genre-overlap heuristic from the cache.
- All responses cached in `artist_cache` for 7 days.
- Backoff on failure: each `artist_cache.fetch_failure_count` failure doubles the next retry interval up to 24 hours.

## Security / privacy

- **Accounts.** Per ADR-006, v1 ships authenticated user accounts (username + password). Username + email are stored lowercased; comparisons run `LOWER() = LOWER()` on both sides to prevent the case-collision bug class.
- **Password hashing.** Argon2id (`m=64 MiB, t=3, p=4`), stored as encoded strings so params can be tuned per-row later. See [ADR-006 § 4.17](decisions/ADR-006-initial-data-schema.md).
- **JWT.** HS256 with `JWT_SECRET` env var. No revocation table in v1; refresh-token `jti` claim makes a v2 additive revocation table possible without schema churn.
- **Email is optional** in v1 — no password-reset flow yet ("contact support" placeholder). Adding reset is a v2 additive (SMTP + `password_reset_token` table).
- **Invite codes.** 8-char Crockford base32; opaque (~1.1T entropy). Anyone with the code can attempt to join, but joining requires an authenticated User. No automatic role hierarchy v1.
- HTTPS in transit (Render enforces this).
- SQLite file relies on OS-level disk encryption if the host provides it; no application-level encryption in v1.
- No third-party trackers, no analytics SDK loaded unless and until we add a self-hosted Plausible.

## Forward-compat watch list

- **SSO** (Apple / Google Sign-In). ADR-006 § 5.6 flags this as an open question; if scoped in, it lands as ADR-007 with an additive `sso_provider` / `sso_subject` column pair on `user`.
- **Refresh-token revocation.** Additive `refresh_token` table later; `jti` claim already in place.
- **Password reset.** Additive `password_reset_token` table + SMTP integration.
- **Multi-event groups.** Schema is event-agnostic at the group level; pivot is straightforward if user need emerges.
- **Real-time push.** Polling → WebSocket migration is contained behind a single hook on the frontend and a separate gateway service on the backend.
- **Database swap.** SQLite → Postgres requires migration script + connection-pool config but no application code changes given SQLAlchemy.

## References

- [PRD.md](PRD.md)
- [ROADMAP.md](ROADMAP.md)
- [decisions/](decisions/) — all ADRs
- [features/](features/) — per-feature specs + ticket harnesses
- [CLAUDE.md](../CLAUDE.md) — repo conventions and hard rules
