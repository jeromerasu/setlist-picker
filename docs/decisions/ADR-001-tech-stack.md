# ADR-001: Tech stack

## Status
Accepted

## Context
setlist-picker is a small group-coordination app: a mobile-friendly web client, a backend API, a small relational data model, and an external music-data integration. Constraints:

- Solo developer for v1 — operational simplicity matters.
- Mobile-friendly: works well in iOS Safari and Android Chrome.
- Offline-capable: the user is at a live event with unreliable Wi-Fi.
- Owner wants Python on the backend (deliberate skill development; healthtech / AI hiring market signal).
- Public open-source repo; contributors should be able to clone and run.

## Decision

- **Web client**: Next.js (App Router) + TypeScript + Tailwind + shadcn/ui. PWA via Workbox-flavored service worker.
- **Backend**: Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + Alembic.
- **Datastore**: SQLite for v1. SQLAlchemy dialect abstraction keeps the Postgres migration cheap.
- **Tooling**: `uv` for Python package management; Turborepo for TypeScript orchestration; Ruff + mypy --strict on Python; ESLint + tsc on TypeScript.
- **Hosting**: Render web service for the API + persistent disk for SQLite; Render Static Site or Vercel for the frontend.

## Rationale

1. **Single backend language.** Python everywhere on the backend keeps the mental model uniform. No Java / Node / Go split. FastAPI's ergonomics are a step up from earlier Python web frameworks (typed handlers, automatic OpenAPI, native async).
2. **SQLite over Postgres for v1.** One file, no separate DB service to deploy + manage, fine for the v1 scale (a few thousand concurrent groups). The cost of swapping later is small because SQLAlchemy abstracts the dialect.
3. **Next.js PWA over native mobile.** Service workers + Web App Manifest cover "feels like an app" without app-store overhead. PWAs install on iOS (with caveats) and Android. App-store distribution is a v2 problem if it ever becomes one.
4. **shadcn/ui over a heavier component library.** Owned components in the codebase, restyled to fit our visual language, no runtime dependency on a third-party design system.
5. **`uv` over Poetry / pip.** Significantly faster install + lockfile resolution. Astral's tooling (`uv` + `ruff`) feels coherent. Reasonable default for new Python projects in 2026.

## Consequences

### Positive
- Single backend language, modern tooling stack, fast iteration.
- PWA covers mobile without native overhead.
- SQLite is "just a file" — backups, copies, local dev environments are trivial.

### Negative
- FastAPI is less "batteries-included" than something like Django — auth, transactions, observability all require deliberate assembly.
- SQLite at scale eventually breaks down (concurrent writes, replication). The plan is to migrate to Postgres before that happens, not after.
- PWA install UX is fragmented on iOS — users may not realize they can "Add to Home Screen."

## References
- [PRD.md](../PRD.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
