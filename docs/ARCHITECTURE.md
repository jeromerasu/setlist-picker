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

## API surface (v1, planned)

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/groups` | POST | Create a group; returns `group_code`. |
| `/api/groups/{code}/join` | POST | Join as a display name; returns `member_id` + cookie. |
| `/api/groups/{code}` | GET | Group state (members, picks). |
| `/api/groups/{code}/picks` | POST | Add a pick: `{member_id, set_id}`. Idempotent via composite PK. |
| `/api/groups/{code}/picks/{set_id}` | DELETE | Remove a pick. |
| `/api/events` | GET | List events (one-per-deploy in v1). |
| `/api/events/{event_id}/lineup` | GET | Full lineup (stages + days + sets). |
| `/api/events/import` | POST | Admin import (paste lineup JSON). Token-gated. |
| `/api/artists/{artist_name}` | GET | Artist drill-down data — backed by `artist_cache`, refreshed against Spotify when stale. |

All responses are JSON, snake_case. See [CLAUDE.md](../CLAUDE.md) for the wire-format convention.

## Real-time strategy

v1: polling. The frontend pulls group state every 5 seconds while the tab is foregrounded. Cheap, no WebSocket infrastructure, easy to reason about.

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

- No PII collected.
- Group code is opaque (8-char base32, ~1.1T entropy) but anyone with the URL has full group access. That's by design — the URL is the credential, like a Google Doc share link.
- Anyone joining is implicitly trusted at the group level. There's no kick / ban / role hierarchy in v1.
- HTTPS in transit (Render enforces this).
- SQLite file encrypted at the OS-level disk encryption layer if the host provides it; no application-level encryption in v1.
- No third-party trackers, no analytics SDK loaded unless and until we add a self-hosted Plausible.

## Forward-compat watch list

- **Auth model.** v2 may want optional "claim my group" via magic link so people can sync across devices without re-pasting the group code. Member ID stays the same; the change is layered on top.
- **Multi-event groups.** Schema is event-agnostic at the group level; pivot is straightforward if user need emerges.
- **Real-time push.** Polling → WebSocket migration is contained behind a single hook on the frontend and a separate gateway service on the backend.
- **Database swap.** SQLite → Postgres requires migration script + connection-pool config but no application code changes given SQLAlchemy.

## References

- [PRD.md](PRD.md)
- [ROADMAP.md](ROADMAP.md)
- [decisions/](decisions/) — all ADRs
- [features/](features/) — per-feature specs + ticket harnesses
- [CLAUDE.md](../CLAUDE.md) — repo conventions and hard rules
