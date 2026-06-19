# Architecture — setlist-picker

System-level decisions. Reflects locked-in choices from the initial design sessions (most recently the 2026-06-18 product clarifications: native mobile, Postgres-from-start, three-provider auth, group↔event 1:1). Update this when something at the system level changes.

## Stack

### Client (apps/mobile)

| Layer | Tech |
|---|---|
| Framework | React Native + Expo + TypeScript |
| Targets | iOS + Android (single codebase, Expo managed workflow) |
| Styling | NativeWind / Tailwind-flavored utility classes |
| State | TanStack Query (server state) + local React state |
| Auth modules | `expo-apple-authentication`, `expo-auth-session` (Google), `expo-secure-store` (JWT) |
| Offline storage | `expo-sqlite` (write queue + cached reads) + `AsyncStorage` (small prefs) |
| Push (deferred) | Expo's unified push service (APNs + FCM behind one token) |
| Build | Expo EAS (binary builds + OTA updates) |

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

**PostgreSQL from V001 baseline.** Per [ADR-001](decisions/ADR-001-tech-stack.md) (revised 2026-06-18), the original SQLite → Postgres ladder is retired. The schema in [ADR-006](decisions/ADR-006-initial-data-schema.md) uses Postgres-specific features (JSONB columns, partial unique indexes, `TIMESTAMPTZ`) directly. Render-managed Postgres for the deploy.

### Hosting

- Backend: Render web service (`services/api`) + Render-managed Postgres.
- Mobile: Expo EAS for binary builds; Apple Developer + Google Play developer accounts for distribution. OTA updates via Expo Updates for JS-only changes.
- External APIs: Spotify (read-only, backend-side; client credentials grant), Apple's JWKS for Sign In with Apple, Google's JWKS for Google Sign-In.

### Monorepo

Single GitHub repo with Turborepo for TypeScript orchestration. Python service lives as a sibling at `services/api` with its own build config (`uv` + `pyproject.toml`). Shared TypeScript types in `packages/types` generated from the OpenAPI schema FastAPI produces.

See [ADR-002](decisions/ADR-002-monorepo-structure.md).

## Data model

**13 tables at V001:** `user`, `group`, `member`, `device`, `event`, `stage`, `set`, `artist`, `artist_source_ref`, `set_artist`, `pick`, `artist_cache`, `group_activity`.

Highlights:

- Groups are 1:1 with Events (mandatory NOT NULL FK `group.event_id`); the FE forces the user to pick a festival up front when creating a group.
- Members are User × Group; leaving a group is a **hard delete** that cascades to that User's picks for the group (`pick.member_id` ON DELETE CASCADE). The mobile client gates the Leave action behind a confirmation dialog.
- Picks tombstone on unpick with a client-assigned `state_clock_ms` for last-write-wins reconciliation.
- Artists are deduplicated globally on `name_normalized`; on lineup re-import the trust-latest-non-null rule preserves a known Spotify ID against payloads that lose it.
- `device` stores push tokens (per User, per device installation); v1 ships the table without yet sending push.
- `group_activity` logs every meaningful in-group event for the feed view + future push pipeline; pruned by a 90-days-or-500-rows-per-group cron sweep that lands in a v1.x ticket.
- UUIDv7 primary keys everywhere except `artist_cache` (`name_normalized` PK) and `group.invite_code` (Crockford base32, distinct from `group.id`).

**The authoritative schema spec — every column, FK, index, design decision, and open question — is [ADR-006: Initial data schema](decisions/ADR-006-initial-data-schema.md).** The Pydantic wire-shape reference for every v1 endpoint is at [docs/schemas/reference/v1_pydantic.py](schemas/reference/v1_pydantic.py).

## Auth model

ADR-006 supersedes ADR-003: v1 ships authenticated user accounts with three first-class providers — **`local` (username + password)**, **`apple` (Sign In with Apple)**, and **`google` (Google Sign-In)**. JWT HS256 access tokens (24h) + refresh tokens (7d); secret in `JWT_SECRET` env var. Every endpoint outside `/auth/*` requires `Authorization: Bearer <access_token>`. Group-scoped endpoints additionally verify the caller is a Member of the group identified by `invite_code`.

See [ADR-006 § 1 Auth model](decisions/ADR-006-initial-data-schema.md) for the full flow and JWT claim shape; § 4.20 covers Apple, § 4.24 covers Google.

## API surface (v1, planned)

Public (no auth required):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/auth/signup` | POST | Create `local`-auth user; returns user + JWT pair. |
| `/api/auth/login` | POST | Username + password → JWT pair. Username comparison `LOWER() = LOWER()`. |
| `/api/auth/apple` | POST | Native Sign In with Apple — `{identity_token, display_name?, email?}` → user + JWT pair. ADR-006 § 4.20. |
| `/api/auth/google` | POST | Native Google Sign-In — `{id_token, display_name?, email?}` → user + JWT pair. ADR-006 § 4.24. |
| `/api/auth/refresh` | POST | Exchange refresh token for a new access + refresh pair. |

Authenticated (Bearer token required):

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/users/me` | GET | Current user. |
| `/api/users/me` | PATCH | Update display name / avatar color / email. |
| `/api/users/me/groups` | GET | All groups the user is a Member of. |
| `/api/users/me/devices` | POST | Register a push token. Idempotent on (user, push_token). |
| `/api/users/me/devices/{device_id}` | DELETE | Revoke a push token (sets `revoked_at`). |
| `/api/groups` | POST | Create a group — `{name?, event_id}` (event_id required; group is 1:1 with event). Returns group + `invite_code`. Creator becomes a Member. |
| `/api/groups/join` | POST | Join via `{invite_code, display_name_override?}`. |
| `/api/groups/{invite_code}` | GET | Group state (members, picks). Polled every 15s; supports `If-Modified-Since` → 304. |
| `/api/groups/{invite_code}` | PATCH | Rename the group. |
| `/api/groups/{invite_code}/leave` | POST | **Hard-delete** the calling Member + cascade-delete their picks. FE shows a confirmation dialog before invoking. |
| `/api/groups/{invite_code}/activity` | GET | Activity feed (newest first, cursor-paginated). |
| `/api/groups/{invite_code}/picks` | POST | Add or upsert a pick. Server runs LWW per ADR-006 § 4.5. `member_id` derived server-side from `(current_user, group)`. |
| `/api/groups/{invite_code}/picks/sync` | POST | Bulk drain of the offline expo-sqlite queue. |
| `/api/groups/{invite_code}/picks/{set_id}` | DELETE | Remove (tombstone) a pick. |
| `/api/groups/{invite_code}/snapshot` | GET | Screenshotable "where will we be at time T" view; per-stage sets in `[at, at + window_minutes]` with **all members'** picks + display names + avatar colors denormalized. No `event_id` query param — the group implies it. ADR-006 § 4.13. |
| `/api/events` | GET | List events available on this deploy. |
| `/api/events/{event_id}/lineup` | GET | Full lineup (stages + days + sets). |
| `/api/events/import` | POST | Admin import (paste lineup JSON). Admin-token-gated; not JWT-gated. |
| `/api/artists/{artist_name}` | GET | Artist drill-down data — backed by `artist_cache`. |

All responses are JSON, snake_case. See [CLAUDE.md](../CLAUDE.md) for the wire-format convention.

## Real-time strategy

v1: polling with conditional GETs (per ADR-006 § 4.14). The mobile app polls `GET /api/groups/{invite_code}` every 15s while the calendar view is foregrounded, 30s while the snapshot view is open. The server returns a `Last-Modified` header derived from `MAX(pick.server_last_updated_at, member.joined_at)` for the group; the client sends `If-Modified-Since` and the server returns **304 Not Modified** when nothing changed. Most polls during quiet periods hit 304 — cheap on metered mobile data.

v2: push notifications (Expo) for "X picked your set"-class events; the `device` table is already in V001 (§ 2.12). WebSockets remain a v3+ option if user reports indicate the polling delay hurts the "who's where right now" feel during the event.

## Offline strategy

See [ADR-004](decisions/ADR-004-offline-strategy.md) (revised 2026-06-18) for the full rationale.

- **`expo-sqlite`** holds the offline write queue, the cached lineup JSON, and the most recent group-state snapshot.
- **`AsyncStorage`** holds small key/value (last-known-server-time, last-selected day tab); JWTs go through `expo-secure-store` (iOS Keychain / Android Keystore).
- **Write queue**: `pending_pick_op(action, set_id, state_clock_ms, queued_at)` rows append on every offline toggle.
- **Reconnect drain**: oldest-first via `POST /api/groups/{invite_code}/picks/sync`. On 2xx, the drained rows delete.
- **Reconciliation** is last-write-wins on `state_clock_ms` (ADR-006 § 4.5). The same `member_id` is used across all of a User's devices; the client clock orders the writes.
- **UI**: "Offline — changes will sync" badge from `NetInfo.isConnected === false` OR last successful poll > 60s ago. Stale-data warning if group cache > 4h old.

## External integrations

### Spotify

Backend-only. Client credentials flow — no user OAuth. The backend stores the client ID + client secret in `services/api/.env`; the mobile client never sees either.

- Endpoints used: search artists by name, get artist details (genres, images), get top tracks.
- Spotify's `related-artists` endpoint was deprecated in late 2024. Fallback chain captured in [ADR-005](decisions/ADR-005-music-data-source.md): try Last.fm `getsimilar`, then a genre-overlap heuristic from the cache.
- All responses cached in `artist_cache` for 7 days.
- Backoff on failure: each `artist_cache.fetch_failure_count` failure doubles the next retry interval up to 24 hours.

### Apple Sign-In (JWKS)

Backend validates Apple identity tokens against `https://appleid.apple.com/auth/keys` (cached). See ADR-006 § 4.20.

### Google Sign-In (JWKS)

Backend validates Google ID tokens against `https://www.googleapis.com/oauth2/v3/certs` (cached). See ADR-006 § 4.24.

## Security / privacy

- **Accounts.** Per ADR-006, v1 ships authenticated user accounts. Username + email are stored lowercased; comparisons run `LOWER() = LOWER()` on both sides to prevent the case-collision bug class.
- **Password hashing.** Argon2id (`m=64 MiB, t=3, p=4`), stored as encoded strings so params can be tuned per-row later. See [ADR-006 § 4.17](decisions/ADR-006-initial-data-schema.md).
- **JWT.** HS256 with `JWT_SECRET` env var. No revocation table in v1; refresh-token `jti` claim makes a v2 additive revocation table possible without schema churn.
- **JWTs on device** are stored via `expo-secure-store` (Keychain / Keystore).
- **Email is optional** in v1 — no password-reset flow yet ("contact support" placeholder). Adding reset is a v2 additive (SMTP + `password_reset_token` table).
- **Invite codes.** 8-char Crockford base32; opaque (~1.1T entropy). Anyone with the code can attempt to join, but joining requires an authenticated User. No automatic role hierarchy v1.
- **Leave-group is destructive**: it cascades to the User's picks for the group. The FE confirmation dialog is a load-bearing safety check (ADR-006 § 4.28).
- HTTPS in transit (Render enforces this).
- No third-party trackers, no analytics SDK loaded unless and until we add a self-hosted Plausible.

## Forward-compat watch list

- **Push notifications.** Table (`device`) is in V001 (ADR-006 § 2.12, § 4.26). v1 doesn't send; pipeline lands in a v1.x ticket.
- **Group activity feed.** Table (`group_activity`) is in V001 with writes; pruning cron (90 days OR 500 rows per group) is a v1.x ticket (ADR-006 § 4.27).
- **Refresh-token revocation.** Additive `refresh_token` table later; `jti` claim already in place.
- **Password reset.** Additive `password_reset_token` table + SMTP integration.
- **Multi-event groups.** Currently 1:1 by design (ADR-006 § 4.25). Schema would need a `group_event` join table + endpoint signature changes if user need ever justifies it; not anticipated.
- **Real-time push.** Polling → WebSocket migration is contained behind a single hook on the mobile client and a separate gateway service on the backend.

## References

- [PRD.md](PRD.md)
- [ROADMAP.md](ROADMAP.md)
- [decisions/](decisions/) — all ADRs
- [features/](features/) — per-feature specs + ticket harnesses
- [CLAUDE.md](../CLAUDE.md) — repo conventions and hard rules
