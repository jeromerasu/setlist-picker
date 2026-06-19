# ADR-001: Tech stack

## Status
**Accepted (revised 2026-06-18).** Supersedes the original "SQLite + Next.js PWA" direction. Postgres from V001 baseline; React Native + Expo mobile client.

## Context
setlist-picker is a small group-coordination app for live festival attendees: a mobile client, a backend API, a small relational data model, and an external music-data integration. Constraints (current as of 2026-06-18):

- Solo developer for v1 — operational simplicity matters.
- **Native mobile target.** Both iPhone and Android ship as v1. The product is a "phone in your pocket at a sweaty festival" tool, not a desktop or browser experience.
- **Offline-capable.** The user is at a live event with unreliable Wi-Fi.
- **Owner wants Python on the backend** (deliberate skill development; healthtech / AI hiring market signal).
- **Public open-source repo;** contributors should be able to clone and run.

## Decision

- **Mobile client**: React Native + Expo + TypeScript. Single codebase for iOS + Android. Expo's managed workflow for v1; ejection deferred until / unless we hit a native-module wall.
- **Backend**: Python 3.12 + FastAPI + Pydantic v2 + SQLAlchemy 2.0 async + Alembic.
- **Datastore**: PostgreSQL from V001 baseline. No SQLite ladder.
- **Tooling**: `uv` for Python package management; `pnpm` + Expo CLI for the RN side; Ruff + mypy --strict on Python; ESLint + tsc on TypeScript.
- **Hosting**: Render web service for the API + Render-managed Postgres; Expo EAS for mobile builds + OTA updates.

## Rationale

1. **Single backend language.** Python everywhere on the backend keeps the mental model uniform. FastAPI's ergonomics (typed handlers, automatic OpenAPI, native async) are a step up from earlier Python web frameworks.
2. **Postgres from day one.** The original ADR specified SQLite for v1 with a "swap later" plan. With the mobile-native pivot and the [ADR-006](ADR-006-initial-data-schema.md) schema landing — 13 tables, partial unique indexes, JSONB columns, `TIMESTAMPTZ` semantics, planned cron-driven prune jobs — Postgres earns its keep on day one. Render-managed Postgres is one click and removes the "two distinct DB dialects to keep in our head" tax. Render disk for SQLite + dialect-abstraction hedging is no longer worth its complexity.
3. **React Native + Expo over Flutter / native.** Single TypeScript codebase covers iOS + Android. Expo bundles the painful native-glue work (Apple Sign-In via `expo-apple-authentication`, Google Sign-In, `expo-sqlite`, `expo-secure-store`, push via Expo's unified service) under one managed workflow. Skill reuse with the existing TS toolchain.
4. **Native over PWA.** App Store distribution earns reliable push, system-level Sign In with Apple, real background sync, and a Share Sheet-native invite-code flow. PWA's iOS install UX is a known papercut; for a phone-only product, the native build is the right answer.
5. **`uv` over Poetry / pip.** Significantly faster install + lockfile resolution. Astral's tooling (`uv` + `ruff`) feels coherent. Reasonable default for new Python projects in 2026.

## Consequences

### Positive
- Single mobile codebase covers both platforms; Expo eats the App Store / Play Store glue.
- Postgres-from-start removes a "swap the DB later" ticket from the roadmap and lets us use JSONB, partial unique indexes, and `TIMESTAMPTZ` semantics directly.
- Render-managed Postgres is operationally close to "one click;" no DB process to babysit on the disk-backed web-service host.
- Sign In with Apple + Google Sign-In + push notifications all become natural fits via Expo modules.

### Negative
- Expo's managed workflow has a real ceiling — if we need a native module Expo doesn't wrap, we eject. Manageable, but a real ticket if it lands.
- Postgres backups + restores are a slightly heavier operational surface than "copy the .sqlite file." Render's managed backups cover this for v1.
- Mobile builds require Apple Developer + Google Play developer accounts (one-time setup + annual fees). Accepted cost of the native pivot.

## Previous direction (PWA + SQLite, retired 2026-06-18)

**The original ADR-001 specified Next.js + Tailwind + shadcn/ui PWA on the frontend and SQLite on the backend, with a planned Postgres migration in v2.** This direction is retired.

Why retired:

- **The product is a phone-in-your-pocket app, not a desktop site.** Jerome confirmed on 2026-06-18 that v1 ships native iOS and Android. The PWA's install-UX papercut on iOS, the "Add to Home Screen" friction, and the lack of system Sign In with Apple are all unacceptable for the at-a-festival use case.
- **SQLite was hedge for an operational simplicity that's no longer there.** The mobile pivot brings real schema complexity ([ADR-006](ADR-006-initial-data-schema.md)) — partial unique indexes, JSONB payloads on `group_activity`, the `device` push-token table, planned cron-driven prune jobs. Render-managed Postgres is one click and eliminates the "two DB dialects in our head" cost.
- **Workbox / IndexedDB / service workers are wrong tools for a native app.** [ADR-004](ADR-004-offline-strategy.md) is being revised in parallel to replace IndexedDB + Workbox with `expo-sqlite` + AsyncStorage. The LWW algorithm survives the swap; only the client-side serialization layer changes.

If the native ship is reversed for any reason, this section is the recovery context — the original PWA stack worked, it's just no longer the best fit for the product we're building.

## References
- [PRD.md](../PRD.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
- [ADR-004 — Offline strategy](ADR-004-offline-strategy.md) — revised in parallel to drop IndexedDB / Workbox.
- [ADR-006 — Initial data schema](ADR-006-initial-data-schema.md) — Postgres-only schema features (JSONB, partial unique, TIMESTAMPTZ).
