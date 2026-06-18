# Roadmap — setlist-picker

Phased plan to a first usable release.

## Phase 0 — Scaffolding (current)

- ✅ Repository created
- ✅ Design docs (PRD, ARCHITECTURE, ADRs, this roadmap)
- ✅ Harness templates (CLAUDE.md, code review template, known-fixes registry, task template, contribution docs)
- ✅ Feature specs for v1 features (calendar, friends list, artist drill-down)
- ✅ Repo conventions (PR template, issue templates, CI workflow stub)

## Phase 1 — Backend foundations (weeks 1–2)

- FastAPI app skeleton with health check + structured logging
- SQLAlchemy 2.0 async setup + first Alembic migration (create the v1 tables: group, member, event, stage, set, pick, artist_cache)
- Pydantic settings + environment management
- Group lifecycle endpoints: create, join, fetch state
- Pick endpoints: add, remove
- Lineup import: JSON file load at app start + admin paste-import endpoint
- Test harness: pytest + httpx async client + sqlite-in-memory fixtures
- CI: lint (Ruff), type-check (mypy --strict), tests

## Phase 2 — Frontend foundations (weeks 2–3)

- Next.js (App Router) scaffold with TypeScript + Tailwind
- shadcn/ui primitives
- Group create / join screens
- Calendar UI (day view first; week view second)
- Pick toggle wired to the backend
- Polling for group state every 5s while tab foregrounded
- OpenAPI → TypeScript type generation pipeline (`packages/types`)

## Phase 3 — Friends list + group view (week 4)

- Top-bar member avatars with assigned colors
- Per-set member dots showing who's going
- "Where is everyone right now?" view

## Phase 4 — Artist drill-down (week 5)

- Spotify client credentials setup
- Artist search → cache → display
- Fallback chain for similar artists (Spotify lookup → Last.fm `getsimilar` → genre-overlap heuristic)
- Backoff on failures
- Artist modal UI with genre / similar artists / top track preview

## Phase 5 — Offline mode (weeks 6–7)

- Service worker registration + Workbox configuration
- Cache-first for lineup + static assets
- IndexedDB write queue
- Reconnect flush + LWW reconciliation
- Offline indicator + stale-warning UI

## Phase 6 — Polish + beta (weeks 8–9)

- Time-conflict warnings on picks
- Accessibility audit (keyboard nav, screen-reader semantics)
- Mobile Safari and Chrome smoke tests on real devices
- Performance pass (bundle size, Lighthouse score)
- Public beta announcement on the repo + a community of choice

## Phase 7 — Public launch (week 10)

- Documentation polished
- "Add to home screen" onboarding hint
- Roadmap clearly communicates "what's next"
- Encourage contributions via Issues + Discussions

## Post-launch (v2 candidates)

- Optional "claim my group" via magic link → cross-device sync.
- Push notifications when friends update picks.
- Multi-event groups (one group, many events).
- WebSocket real-time push instead of polling.
- Postgres swap once scale demands.
- Native mobile app via the existing PWA codebase wrapped in something like Tauri or Expo's webview.
- Cohort analytics on which sets get the most group-picks (aggregate, privacy-preserving).

## How phases are sized

Each phase is sized at ~5–10 tickets. Tickets live under `docs/features/<feature>/tickets/` (see the journal feature in the byb-frontend repo for the pattern). Each ticket is fire-and-implement: an AI session (or human) reads it, executes, opens a PR. CLAUDE.md hard rules apply.
