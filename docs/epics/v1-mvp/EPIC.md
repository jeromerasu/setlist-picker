# EPIC — setlist-picker v1 MVP

**Status:** Design — awaiting Jerome sign-off before any ticket is opened in GitHub.
**Last updated:** 2026-06-23
**Source prototype:** [`.local-data/design/FestApp.dc.html`](../../../.local-data/design/FestApp.dc.html) — Cosmic-Neon, 7 screens.
**Authoritative schema:** [ADR-006](../../decisions/ADR-006-initial-data-schema.md).
**Authoritative wire shapes:** [`docs/schemas/reference/v1_pydantic.py`](../../schemas/reference/v1_pydantic.py).

---

## 1. What we are shipping

A native iOS + Android app (React Native + Expo) backed by a FastAPI + Postgres service, deployed on Render. The user opens the app, signs in (Apple / Google / local), creates or joins a group scoped to a single festival, picks the sets they want to see, and sees who in the group is going where — refreshed every 15s via conditional GETs. The seven screens in the chosen prototype are the v1 surface.

The story we are NOT shipping in v1: push notifications send pipeline (table is in V001; send is v1.x), light theme (dark only — promoted to a BACKLOG ticket per § 7 OQ-04), multi-event groups, direct messaging, friend requests across groups, full-track playback (30s Spotify preview only). The PRD's pre-pivot "no-account" language is superseded by [ADR-006](../../decisions/ADR-006-initial-data-schema.md) — PRD reconciliation is filed as OQ-05.

## 2. Locked stack (from PR #1 and PR #2)

| Layer | Decision | Source |
|---|---|---|
| BE framework | FastAPI + uvicorn + Python 3.12 + uv | [ARCHITECTURE.md § Stack](../../ARCHITECTURE.md) |
| BE quality bar | pytest + pytest-asyncio + ruff + mypy --strict | [CLAUDE.md § Hard Rules](../../../CLAUDE.md) |
| Database | PostgreSQL (Render managed), SQLAlchemy 2.0 async + Alembic | [ADR-001](../../decisions/ADR-001-tech-stack.md) revised 2026-06-18 |
| Wire JSON | snake_case end-to-end (Pydantic v2 + matching TS interfaces) | [CLAUDE.md § API Conventions](../../../CLAUDE.md) |
| Auth | Option C — Apple Sign-In + Google Sign-In + local username/password. JWT HS256 (24h access / 7d refresh). | [ADR-006 § 1, § 4.20, § 4.24](../../decisions/ADR-006-initial-data-schema.md) |
| Group ↔ Event | 1:1, NOT NULL FK `group.event_id`. FE forces an event pick up front. | [ADR-006 § 4.25](../../decisions/ADR-006-initial-data-schema.md) |
| Invite code | 8-char Crockford base32, doubles as group URL token. No expiry, no rotation. | [ADR-006 § 4.11, § 4.22](../../decisions/ADR-006-initial-data-schema.md) |
| Member lifecycle | Hard delete on Leave; cascade to picks. FE confirmation dialog is a load-bearing safety net. | [ADR-006 § 2.3, § 4.28](../../decisions/ADR-006-initial-data-schema.md) |
| Pick concurrency | Last-write-wins on client-assigned `state_clock_ms`. Reject if > 1h ahead of server clock (recommendation 5.3 (B)). | [ADR-006 § 4.5, § 5.3](../../decisions/ADR-006-initial-data-schema.md) |
| Artist dedup | Upsert on `name_normalized`; trust-latest-non-null on `spotify_artist_id`, `image_url`, `social_links`. | [ADR-006 § 4.29](../../decisions/ADR-006-initial-data-schema.md) |
| Real-time | Polling — 15s for group state, 30s for snapshot — with `Last-Modified` / `If-Modified-Since` → 304. | [ADR-006 § 4.14](../../decisions/ADR-006-initial-data-schema.md) |
| FE framework | React Native + Expo + TypeScript. NativeWind for utility classes. TanStack Query for server state. expo-secure-store for JWT. expo-sqlite + AsyncStorage for offline. | [ADR-001 (revised)](../../decisions/ADR-001-tech-stack.md) |
| Hosting | Render web service for `services/api` + Render-managed Postgres. Expo EAS for mobile binaries. | [ARCHITECTURE.md § Hosting](../../ARCHITECTURE.md) |
| Push | `device` table in V001. Send pipeline + APNs/FCM setup deferred to v1.x. v1 only ships the registration plumbing. | [ADR-006 § 2.12, § 4.26](../../decisions/ADR-006-initial-data-schema.md) |

## 3. Discipline that applies to every ticket

Each ticket in this epic — Wave 1, 2, 3 — must contain all ten sections in [`TICKET_TEMPLATE`](#ticket-template) below before it can be picked up. Per Jerome's 2026-06-22 specificity bar:

> Before writing each ticket body, meta-prompt yourself: *"What does this ticket need to contain for the result to be considered acceptable?"* Then write that into the ticket. If a senior engineer picks the ticket cold and can't answer (a) "what exactly do I build?" (b) "how do I prove it's right?" (c) "what do I NOT build?" — the ticket isn't ready.

The Section 7 (Acceptable validation) of each ticket lists **exact test names with their assertions**, not "tests green." If the implementer can't grep `pytest` / `npm test` output for the test names from the ticket and check them off one by one, the ticket is under-specified.

Cross-cutting hard rules from [CLAUDE.md](../../../CLAUDE.md) and [`code_review_known_fixes.md`](../../code_review_known_fixes.md) that apply to every ticket — implementers don't get to re-litigate them:

- Backend: `pytest` + `ruff check .` + `mypy --strict` must be green before the PR opens. No suppressions.
- Backend: no bare `except Exception` in service-layer code (NF-005). Top-level FastAPI handlers may, but must `logger.exception(...)` the traceback.
- Frontend: `npm test` + `tsc --noEmit` must be green. Snake_case TS interfaces for API payloads (CLAUDE.md § API Conventions cautionary tale).
- Alembic: run `ls services/api/alembic/versions/ | tail -5` before generating; NF-006 forbids parallel-created migrations.
- Every PR touching code updates [`docs/CODEBASE_GUIDE.md`](../../CODEBASE_GUIDE.md) when it adds, removes, or renames a class, endpoint, or significant module.
- Feature branches + PRs + squash-merge only. No direct pushes to main.
- One ticket = one PR. Max 2–3 files per BE ticket; 1 page/component per FE ticket. Broader scope causes session hangs.
- FE `git add` in BE sessions MUST use explicit paths.
- Structured logging on every failure, fallback, and non-obvious decision. Event tag + entity IDs + traceback via `logger.exception(...)`.

## 4. Phasing — three waves with explicit dependencies

```
WAVE 1 (BE foundation)             WAVE 2 (data + FE shell)            WAVE 3 (FE screens)
─────────────────────────          ─────────────────────────           ───────────────────
BE-001 scaffold                ──> BE-012 events list                  FE-001 groups list
BE-002 V001 baseline migration  └─> BE-013 lineup detail               FE-002 create group
   ├─> BE-003 auth local       ──> BE-014 group sets + picks           FE-003 event picker
   ├─> BE-004 auth apple        └─> BE-015 POST picks                  FE-004 join group
   ├─> BE-005 auth google        └─> BE-016 DELETE picks               FE-005 group detail
   ├─> BE-006 group create        ─> BE-017 snapshot endpoint          FE-006 schedule (biggest)
   ├─> BE-007 group join          ─> BE-018 lineup importer            FE-007 artist modal
   ├─> BE-008 my groups          ─> BE-019 artist data fetcher         FE-008 right-now snapshot
   ├─> BE-009 group state        ─> BE-020 device registration         FE-009 account / profile
   └─> BE-010 group members           FE-100 Expo init + nav shell
       BE-011 Render deploy            FE-101 design-tokens + primitives
                                       FE-102 auth flow (Apple/Google/local)
```

Edges read top-to-bottom (Wave 1 lands before Wave 2 lands before Wave 3). Within a wave, tickets are mostly independent and can be picked up in parallel. The two exceptions inside Wave 1 are explicit: every auth/group/member ticket depends on BE-002 (the migration). Inside Wave 3, FE-006 (schedule) implicitly depends on FE-101 (primitives) being merged.

## 5. Ticket inventory

### Wave 1 — BE foundation (must ship first)

| ID | Title | Wave-internal blocker | Why this lands first |
|---|---|---|---|
| [BE-001](./BE-001-repo-scaffold.md) | FastAPI repo scaffold (uv + pytest + ruff + mypy --strict + structlog) | — | Every other BE ticket needs the app entry point + test harness. |
| [BE-002](./BE-002-v001-baseline-migration.md) | V001 Alembic baseline migration (13 tables per ADR-006) | BE-001 | Every auth/group/event/pick ticket talks to these tables. |
| [BE-003](./BE-003-auth-local.md) | `POST /api/auth/{signup,login,refresh}` + `GET /api/users/me` + `PATCH /api/users/me` | BE-002 | Local-credential path; gates every non-`/auth/*` endpoint via the JWT dependency. |
| [BE-004](./BE-004-auth-apple.md) | `POST /api/auth/apple` — Sign In with Apple (JWKS validation + Q5) | BE-003 | App Store Guideline 4.8: required v1 once Google ships. |
| [BE-005](./BE-005-auth-google.md) | `POST /api/auth/google` — Google Sign-In (JWKS validation + Q6) | BE-003 | Table-stakes on Android per [ADR-006 § 4.24](../../decisions/ADR-006-initial-data-schema.md). |
| [BE-006](./BE-006-group-create.md) | `POST /api/groups` — create group, assign 8-char Crockford invite code, auto-create creator's Member row | BE-003 | The create-group flow's BE half. |
| [BE-007](./BE-007-group-join.md) | `POST /api/groups/join` — idempotent join by invite code | BE-003 | The join-group flow's BE half. |
| [BE-008](./BE-008-my-groups.md) | `GET /api/users/me/groups` — caller's group list (Q3) | BE-003 | Powers the home screen. |
| [BE-009](./BE-009-group-state.md) | `GET /api/groups/{invite_code}` — group state with members + picks; `Last-Modified` / `If-Modified-Since` / 304 | BE-003 | The 15s-poll endpoint that backs the schedule view. |
| [BE-010](./BE-010-group-members.md) | Member roster query path (covered by BE-009's response shape; this ticket adds the `MemberOut` resolution helper + tests) | BE-003 | Confirms the COALESCE rule for display name resolution. |
| [BE-011](./BE-011-render-deploy.md) | `render.yaml` + env-var docs + smoke-deploy a `/healthz` route | BE-001 | Without this, nothing is reachable from a real device. |

### Wave 2 — BE data path + FE shell

| ID | Title | Wave-internal blocker | Notes |
|---|---|---|---|
| [BE-012](./BE-012-events-list.md) | `GET /api/events` — list events on this deploy (search by name/location) | BE-002 | OQ-03 affects whether this is curated or open. |
| [BE-013](./BE-013-event-lineup.md) | `GET /api/events/{event_id}/lineup` — stages + sets + artists | BE-002 | Read-only; one query per event. |
| [BE-014](./BE-014-group-sets-with-picks.md) | The pick payload denormalization in `GET /api/groups/{invite_code}` (Q1 SQL) | BE-009 | Adds `PickSummary[]` to the group state response. Same endpoint as BE-009 but this ticket is the picks half of it. |
| [BE-015](./BE-015-pick-create.md) | `POST /api/groups/{invite_code}/picks` + `POST .../picks/sync` — single pick + bulk drain. LWW per § 4.5. | BE-009 | Server derives `member_id` from `(current_user, group)`. |
| [BE-016](./BE-016-pick-delete.md) | `DELETE /api/groups/{invite_code}/picks/{set_id}` — tombstone unpick | BE-015 | Same LWW guard. |
| [BE-017](./BE-017-snapshot.md) | `GET /api/groups/{invite_code}/snapshot?at=&window_minutes=` — Q2 SQL | BE-009, BE-013 | Powers the share/screenshot view. |
| [BE-018](./BE-018-lineup-importer.md) | `scripts/import_lineup.py` + `POST /api/events/import` admin endpoint, with the `event_api_v1` adapter | BE-002 | One-shot CLI for ops; admin endpoint is paste-import via admin token. |
| [BE-019](./BE-019-artist-fetcher.md) | Artist data fetcher: `GET /api/artists/{artist_name}` cache-first → Spotify → Last.fm → genre-overlap heuristic | BE-002 | 7-day TTL; backoff per [ADR-005](../../decisions/ADR-005-music-data-source.md). |
| [BE-020](./BE-020-device-register.md) | `POST /api/users/me/devices` + `DELETE /api/users/me/devices/{device_id}` — idempotent registration / revoke | BE-003 | Plumbing only; no send pipeline. |
| [FE-100](./FE-100-expo-init-nav-shell.md) | Expo init + 5-tab nav (`Home / Search / You` per prototype) + TanStack Query + secure-store JWT | — | The prototype only shows 3 tabs (Home / Search / You) — see OQ-01. |
| [FE-101](./FE-101-design-tokens-primitives.md) | Implement [DESIGN-TOKENS](./DESIGN-TOKENS.md) as NativeWind config + reusable primitives (`GlassCard`, `NeonGradientButton`, `AvatarStack`, `StagePillButton`, gradient text component) | FE-100 | Every Wave-3 screen depends on these. |
| [FE-102](./FE-102-auth-flow.md) | Auth screens: launch → choose provider → Apple / Google / local. Wires `expo-apple-authentication`, `expo-auth-session`, and a local username/password form to BE-003/004/005. | FE-100, BE-003, BE-004, BE-005 | First chrome the user sees on a fresh install. |

### Wave 3 — FE screens (7 prototype screens + account + snapshot)

| ID | Title | Maps to prototype `sc-if` | Notes |
|---|---|---|---|
| [FE-001](./FE-001-groups-list.md) | Groups list (Home screen) | `isGroups` | Empty state with CTA when no groups. |
| [FE-002](./FE-002-create-group.md) | New-group form | `isCreate` | Two fields: group name + event picker entry. |
| [FE-003](./FE-003-event-picker.md) | Event picker with search | `isEventPicker` | Opens from FE-002 and from "join → pick event" if user changes mind. |
| [FE-004](./FE-004-join-group.md) | Invite-code entry | `isJoin` | 8-char Crockford normalization on input. |
| [FE-005](./FE-005-group-detail.md) | Group detail + member roster + Artists tabs (All / Day 1..4) | `isGroup` | Shows invite code w/ copy-to-clipboard + Share Sheet. |
| [FE-006](./FE-006-schedule.md) | Schedule — All Stages grid view + Schedule timeline + Mine/Group filters + day menu + filter sheet | `isSchedule` | Largest FE ticket. Two sub-tabs, multiple empty states. |
| [FE-007](./FE-007-artist-modal.md) | Artist detail (cyber-retro accent) | `isArtist` | Spotify top tracks + similar artists + "X friends going" indicator. |
| [FE-008](./FE-008-right-now-snapshot.md) | "Right Now" snapshot view + screenshot-share UX | (new screen — not in prototype) | Hooks `BE-017` snapshot endpoint. Adds a `react-native-view-shot` capture + Share Sheet. |
| [FE-009](./FE-009-account-profile.md) | Account / profile (display name, avatar color, logout, leave-group confirmation copy) | (new screen — not in prototype) | The prototype's bottom-nav "You" leads here. |

**Ticket count: 32 (11 Wave 1 + 12 Wave 2 + 9 Wave 3).** EPIC.md + DESIGN-TOKENS.md = 2 design docs.

## 6. Ticket template

Every ticket file in this epic uses the same 10-section structure. The headings are mandatory; subheadings vary by ticket type (BE vs FE).

```markdown
# {ID} — {Title}

**Wave:** 1 | 2 | 3
**Type:** BE | FE | Infra
**Blocked by:** {ticket IDs}
**Blocks:** {ticket IDs}
**ADR references:** {section anchors}

## 1. Problem statement
2–4 sentences. The user-facing or system behavior this ticket delivers.

## 2. Actual solution
Prose algorithm. Data flow. Where in the codebase. NOT "implement X."

## 3. Files to touch
| Path | Edit purpose |

## 4. Method signatures / new APIs
Full Pydantic models (snake_case), TS prop types, endpoint contracts with sample
request/response, exact route + verb + status codes.

## 5. Constants and thresholds
Exact numbers with rationale. No TBD.

## 6. Edge cases enumerated
Every case the implementer must handle, with expected behavior for each.

## 7. Acceptable validation
- Test files + test names that MUST exist with their assertions
- Manual QA steps (light + dark mode for FE — prototype is dark-only, but call
  out if a light variant exists)
- Structured-log lines emitted on success
- Failure modes + user-facing behavior
- "All tests green" is NOT acceptance.

## 8. Out of scope
Explicit list, with follow-up ticket references.

## 9. Structured-log events
Event tags + field schemas.

## 10. Rollback plan
What to revert if broken.
```

## 7. Open questions for Jerome

These are flagged at the EPIC level because they change ticket scope across multiple files. None should be resolved by an implementer mid-flight.

| ID | Question | Recommendation | Affected tickets |
|---|---|---|---|
| **OQ-01** | The prototype's bottom-nav is **3 tabs** (Home / Search / You). The task brief describes **5 tabs** (Home / Favorites / Schedules / Artists / Groups). Which is v1? | **Ship 3 tabs to match the prototype.** Favorites/Schedules/Artists are reachable from the Groups → Group → Schedule path; a global 5-tab nav adds entry points we don't have screens for yet. Promote to 5 in v2 once those screens exist. | FE-100, FE-001 |
| **OQ-02** | Artist detail uses a **mixed cyber-retro aesthetic** (VT323 + green Spotify pill + heavy scanlines) that diverges from the Cosmic-Neon main app. Keep the mixed-aesthetic call, or normalize to Cosmic-Neon? | **Keep the mixed aesthetic.** It signals "you've entered an artist's world" without ambiguity, and the divergence is intentional in the prototype. Document the divergence in `DESIGN-TOKENS.md § 5` so it doesn't read as inconsistency. | FE-007, DESIGN-TOKENS |
| **OQ-03** | Featured-festivals list in the Event Picker — what's the v1 source? Curated by us? User-submitted? TML 2026 W2 only? | **Curated, hardcoded seed of ~7 events** (matching the prototype's `EVENTS` array) populated via [BE-018](./BE-018-lineup-importer.md) `scripts/import_lineup.py` for v1 launch. User-submitted events promoted to v2; TML 2026 W2 is the test fixture we round-trip against (per [ADR-006 Context](../../decisions/ADR-006-initial-data-schema.md)). | BE-012, BE-018 |
| **OQ-04** | Light theme — defer or partial v1? | **Defer to a BACKLOG ticket.** Prototype is dark-only; no Cosmic-Neon-light palette designed yet; standing rule against fuzzy v2 work. Encode this as `BACKLOG-001-light-theme.md` (out of scope here). FE tickets will still note "dark mode only — light theme is BACKLOG-001" so a future reader knows it was a deliberate omission, not a miss. | All FE tickets |
| **OQ-05** | The [PRD](../../PRD.md) § 1, § 2, § 4 still encode the pre-pivot anonymous model. ADR-006 § 5.1 already flagged this. When does the PRD reconciliation PR land — before, alongside, or after this epic? | **Alongside Wave 1.** A PRD that still claims "no account" while V001 ships JWT auth is harmful to onboarding new contributors. Open a separate `docs/PRD.md` reconciliation PR while Wave 1 BE tickets are in flight. | Not a ticket here — separate `docs/` PR. |
| **OQ-06** | Push notifications in v1: just the device registration endpoint, or the full send pipeline + APNs/FCM credentials? | **Registration plumbing only, per [ADR-006 § 4.26](../../decisions/ADR-006-initial-data-schema.md).** Send pipeline + EAS credentials lands as v1.x ticket `BACKLOG-002-push-send-pipeline.md`. v1 ships `BE-020` so when push lands the table is already hot. | BE-020 |
| **OQ-07** | Member color UX regression — § 4.12 / § 5.5 of ADR-006. Two users with the same `user.avatar_color` look identical in a group. Accept, override at Member, or render-time tiebreak? | **Accept for v1** (matches ADR-006 § 5.5 (A) recommendation). FE-005's member roster + FE-006's grid avatars use the User's `avatar_color` verbatim. If user feedback hurts, promote to `BACKLOG-003-member-color-tiebreak.md`. | FE-005, FE-006 |
| **OQ-08** | Clock-skew tolerance on pick LWW (ADR-006 § 5.3). Accept any client clock, or reject `state_clock_ms > server_now + 1 hour`? | **Reject (option B).** Lands inside BE-015. The 1-hour buffer is generous for any plausible device-clock drift, and rejecting protects every other member from a future-clock attacker pinning their `state` field permanently. | BE-015 |

## 8. Cross-stack risks (spotted while reading the prototype against the schema)

These are NOT open questions — they have answers — but they affect more than one ticket and should be on every implementer's radar.

1. **The prototype's `picks` shape is `{set_id: 'going' | 'maybe'}` — a tri-state. The backend pick model is binary `active | tombstoned`.** "Maybe" is a prototype-only convenience. Wave-3 FE-006 must collapse the tri-state down to **only the `going` lobe sending a pick to the server**; the `maybe` lobe is local-state-only or quietly dropped. Don't extend the schema to add `state = 'maybe'` — the snapshot endpoint depends on `active` meaning "going."
2. **The prototype's `goingMembers(set)` resolves the calling user via `this.ME`.** The backend response from [BE-009](./BE-009-group-state.md) returns picks keyed by `member_id`. The FE must resolve "is this me?" by matching the response's `members[]` (which carries `user_id`) against the JWT-decoded `current_user.id`, not by client-side identity assumptions.
3. **The prototype's `cycleGrid` uses optimistic state mutation** with no LWW handling. FE-006 must wrap pick toggles with a `state_clock_ms = Date.now()` write to expo-sqlite first, then POST. If the POST fails or the response says `accepted: false`, the FE reconciles by re-reading the polled `GroupStateResponse.picks[]` — the server is authoritative.
4. **The prototype's day tabs (`Day 1..4`) are stage-grouped by `s.day === 1..4`.** The backend stores `set.day_label` as the source-provided string (`FRIDAY`, `SATURDAY`, etc.) per [ADR-006 § 2.6](../../decisions/ADR-006-initial-data-schema.md). FE-005 and FE-006 must derive day buckets by `day_label`, not by integer day numbers. The "Day N" UI label is a render-time mapping (in `event.timezone`-local order), not data the BE returns.
5. **The prototype shows the invite code as `{{ G.code }}` rendered in a monospace pill and copied via a toast — no Share Sheet.** The native target (Expo) gets `expo-sharing` for free; FE-005 should add the Share Sheet path *in addition to* the copy-to-clipboard fallback, since prototype-fidelity ≠ native-platform-fidelity.
6. **Spotify ID drift on artist re-import** — the prototype has no concept of re-import. [ADR-006 § 4.29](../../decisions/ADR-006-initial-data-schema.md)'s trust-latest-non-null rule applies to BE-018 and must be tested with the regressing-payload case (the test name is in BE-018 § 7).
7. **The prototype's `ARTMETA` is hardcoded.** [BE-019](./BE-019-artist-fetcher.md) ships real Spotify/Last.fm calls, which means rate limits + key management + cache TTL. The prototype's instant artist-data assumption does not survive contact with the network; the FE must show a "loading similar artists" skeleton (per [artist-drilldown-spec § Design integrity](../../features/artist-drilldown-spec.md)).
8. **No "Right Now" view in the prototype.** FE-008 is a new screen; its design is described in this epic but not visually prototyped. Jerome may want a separate design pass before FE-008 is opened. The ticket files BE-017 (endpoint) and FE-008 (consumer) are decoupled enough that BE-017 can land first regardless.

## 9. Definition of Done for the epic

The epic is closed when:

1. Every ticket file listed in § 5 is merged with a passing CI run.
2. A real human can:
   - install the Expo dev build on iPhone or Android,
   - sign in via any of the three providers,
   - create a group, see the invite code, share it,
   - have a second human join, see both members,
   - pick a set from the schedule, have the first user see the pick within 15s,
   - tap an artist and see real Spotify data,
   - open the "Right Now" snapshot and share a screenshot.
3. `docs/CODEBASE_GUIDE.md` reflects every endpoint + module added.
4. `docs/PRD.md` has been reconciled (OQ-05) — the v1 PRD no longer claims "no account, no email, no signup."

## 10. References

- [PRD.md](../../PRD.md) — product requirements (OQ-05: needs reconciliation).
- [ARCHITECTURE.md](../../ARCHITECTURE.md) — locked stack + API surface table.
- [ADR-001 Tech stack (revised 2026-06-18)](../../decisions/ADR-001-tech-stack.md)
- [ADR-002 Monorepo structure](../../decisions/ADR-002-monorepo-structure.md)
- [ADR-003 Auth model — SUPERSEDED](../../decisions/ADR-003-auth-model.md)
- [ADR-004 Offline strategy (revised 2026-06-18)](../../decisions/ADR-004-offline-strategy.md)
- [ADR-005 Music data source](../../decisions/ADR-005-music-data-source.md)
- [ADR-006 Initial data schema + auth (2026-06-18 locked)](../../decisions/ADR-006-initial-data-schema.md)
- [features/calendar-spec.md](../../features/calendar-spec.md) — Wave-3 FE-006 baseline
- [features/friends-list-spec.md](../../features/friends-list-spec.md) — Wave-3 FE-005 / FE-008 baseline (NB: BE-FL-002 dead per ADR-006 § 4.12)
- [features/artist-drilldown-spec.md](../../features/artist-drilldown-spec.md) — Wave-3 FE-007 baseline
- [`docs/schemas/reference/v1_pydantic.py`](../../schemas/reference/v1_pydantic.py) — wire shapes
- [`code_review_template.md`](../../code_review_template.md) + [`code_review_known_fixes.md`](../../code_review_known_fixes.md) — review bar
- [`.local-data/design/FestApp.dc.html`](../../../.local-data/design/FestApp.dc.html) — chosen Cosmic-Neon prototype
- [`.local-data/design/competitor-reference/`](../../../.local-data/design/competitor-reference/) — Jerome's reference screenshots
