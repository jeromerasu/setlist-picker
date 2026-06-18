# Code Review — Known Fixes & Rules

Living registry of recurring traps and the rules that catch them. Add to this file when a hotfix or review surfaces a general rule worth institutionalizing. Each entry includes the **Rule**, **Why** (with commit reference when applicable), and **How to apply** during review.

Linked from [`code_review_template.md`](code_review_template.md). Reviewers must skim this file before sign-off. PRs that violate any NF-NNN rule are auto-blocked.

---

## Next.js / React Hydration

### NF-001 — `'use client'` directive MUST be the first syntactic element in the file

**Rule:** No comments, ESLint-disables, or any other syntactic content may precede `'use client'`. The directive must be on line 1. If an ESLint-disable is needed, it goes on line 2.

**Why:** Next.js's SWC transform requires `'use client'` to be the very first syntactic element. A block comment before it silently demotes the file to a Server Component. Server Components throw on `useState` / `useEffect` calls, cascading into portal-wide React #418 hydration loops that take down every route. Real production bug from byb-coach-portal 2026-06; this rule ports cleanly to any Next.js codebase.

**How to apply:**
- Grep new client components: `grep -l "useState\|useEffect" apps/web/src/components/**/*.tsx | xargs head -1` → every result should be exactly `'use client'`.
- For any client component touched, open the file and verify line 1 by eye.

---

## API Contract & Wire Shape

### NF-002 — FE types matching BE DTOs MUST be verified against the actual wire shape

**Rule:** Any TypeScript interface that mirrors a Pydantic model MUST be reconciled against (a) the Pydantic source-of-truth AND (b) an authenticated curl against the live dev endpoint, before the PR is merged.

**Why:** Field-name drift between Pydantic and TypeScript is silent at compile time. Snake_case vs camelCase mistakes don't fail the build — they fail at the wire, with broken downstream data and no 400. Tests that mock at the hook level also miss this because they use whatever fixture shape they were written with.

**How to apply:**
- Locate the BE Pydantic source-of-truth (e.g. `services/api/app/models/group.py`) and read every field name.
- Run an authenticated curl against the live dev endpoint and confirm the JSON keys match what the FE type expects.
- Verify FE test fixtures use the same field names as the live response.
- If `packages/types` is set up to auto-generate from OpenAPI, regenerate after every endpoint change.

---

## React State & Data Flow

### NF-003 — Render-time `.map()` MUST guard against `undefined`

**Rule:** Every `.map()` / `.some()` / `.length` access on a value that comes from a query result must guard with `?? []` or an early-return. TanStack Query's typed `data` is `T | undefined` during loading.

**Why:** Unguarded access throws at initial render, fires the error boundary, and looks like a backend bug to the user when it's actually a frontend defensive-coding miss. Saw this multiple times in byb-coach-portal across the D3 wave.

**How to apply:**
- Grep the PR diff for `.map(` calls: `git diff main..HEAD | grep -nE '\.map\('`.
- For each, confirm the value is either a literal array, guarded with `?? []` / `?.map`, or inside an early-return when `data` is undefined.
- Pure TanStack-typed `data.field.map(...)` without a guard = block PR.

---

## SSR / Server-side Boundary

### NF-004 — No top-level `localStorage` / `window` / `document` / cookie reads in code shared across SSR

**Rule:** Module-load-time access to browser-only APIs causes silent SSR errors that surface as React #418 hydration cascades (paired with NF-001) or as 500s on first request. Helpers must defer browser-API reads until they're called from a callback / effect, gated with `typeof window !== 'undefined'`.

**Why:** Same family of bug as NF-001. Helpers that auto-inject `user_role` from a cookie or `route_path` from `window.location` must do the read lazily.

**How to apply:**
- Grep the PR diff: `git diff main..HEAD | grep -nE '^\+.*(localStorage|sessionStorage|window\.|document\.|cookie)'`.
- For each `+` line, confirm it's inside a function body, a `useEffect`, or a callback — not at module top level.

---

## Python — Service Layer

### NF-005 — No bare `except Exception` in service code

**Rule:** Service-layer code catches specific exception types (`httpx.HTTPError`, `sqlalchemy.exc.IntegrityError`, `TimeoutError`, `OSError`, etc.). Programming errors (`AttributeError`, `KeyError`, `TypeError`) bubble up.

**Why:** Broad `except Exception` swallows programming bugs. A typo or null deref gets logged as "external API failure" or "DB error" when it's really a logic bug. Future debugging spends hours chasing the wrong cause.

**How to apply:**
- Grep new service code: `git diff main..HEAD -- services/api/app/services/ | grep -nE '^\+.*except Exception'`.
- Top-level FastAPI exception handlers MAY broad-catch but MUST log the full traceback via `logger.exception(...)`.

---

## Alembic — Migrations

### NF-006 — Never create migrations in parallel tasks

**Rule:** Before creating an Alembic migration, run `ls services/api/alembic/versions/ | tail -5` to find the latest version number. Use the next number. Never have two open PRs with new migration files — version numbers collide silently and Alembic's history breaks.

**Why:** Alembic version chains by parent revision ID, not by filename ordering. Two parallel PRs that both add `revision = "abc123"` as the latest end up in an inconsistent state at merge time. Recovery requires hand-editing migration files.

**How to apply:**
- Check open PRs for `alembic/versions/*.py` files. If any open PR adds a migration, hold yours until theirs merges (or coordinate explicitly).
- After merging a migration PR, immediately rebase any other open PRs that have local migrations and re-run `alembic upgrade head` to verify chain integrity.

---

## How to add a new entry

When a PR review or production hotfix surfaces a general rule worth institutionalizing:

1. Append a new section (NF-NNN) under the appropriate category, or add a new category if needed.
2. Reference the commit / PR that surfaced it.
3. Include a concrete grep / verification pattern under "How to apply".
4. Submit as a separate PR or bundle with the originating hotfix.
