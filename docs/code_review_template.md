# Code Review Template — setlist-picker

Use this template for every PR review. Reviewers fill out each section explicitly — "looks good" is not a review.

Before sign-off, skim [`code_review_known_fixes.md`](code_review_known_fixes.md). PRs that violate any NF-NNN rule are auto-blocked.

---

## 1. Scope & Correctness vs Spec

- What ticket does this PR claim to close? (Link.)
- Does the diff match the ticket's stated scope?
- Any scope creep — files touched that the ticket didn't list?
- Acceptance criteria all met?

## 2. API Contract & Wire Compatibility

- Backend: Pydantic models use snake_case fields.
- Frontend: TypeScript interfaces consuming the API use snake_case fields.
- OpenAPI schema regenerated; `packages/types` updated.
- Existing endpoints unchanged unless the PR is explicitly evolving them.

## 3. Security & Authorization

- No secrets committed (search `.env`, `SPOTIFY_CLIENT_SECRET`, etc.).
- Group code is the credential; no endpoint accepts requests without one (or admin token for admin endpoints).
- No unsafe SQL — SQLAlchemy ORM or properly-bound text queries only.
- External-API responses validated before persisting.

## 4. Data Integrity & Persistence

- Migrations are reversible (`alembic downgrade` works).
- Migration version is sequential — no parallel-created migrations.
- DB writes are inside a transaction where atomicity matters.
- Idempotent endpoints actually idempotent (composite PKs, upserts, replay-safe).

## 5. Error Handling & Observability

- No bare `except Exception` in service code (NF-002).
- Caught exceptions are specific (`httpx.HTTPError`, `sqlalchemy.exc.IntegrityError`, etc.).
- `logger.exception(...)` used for unexpected failures (captures traceback).
- Structured logging: event tag + entity IDs + relevant context.
- Top-level FastAPI exception handlers re-raise to the framework or return a structured error response, never silently swallow.

## 6. Performance & N+1

- Repeated queries inside loops? Use `selectinload` / `joinedload` to eager-load.
- Cache hits actually hit (verify the cache key).
- No accidental full-table scans (look for missing indexes on filter columns).

## 7. Code Health & Maintainability

- File / module organization matches existing patterns.
- No dead code (commented-out blocks, unused imports).
- Names are honest (no `data` / `tmp` / `helper`).
- Functions ≤ ~40 lines; classes ≤ ~250 lines unless there's a real reason.
- Type hints on every function signature; `mypy --strict` passes.

## 8. Test Coverage & Quality

- Happy path + at least one edge case per behavior.
- Auth-denial tests for protected endpoints.
- Error-path tests: 4xx + 5xx scenarios.
- Async tests use `pytest-asyncio`.
- Tests mock external APIs (no real Spotify calls in CI).
- Frontend: at least snapshot + interaction test per non-trivial component.

## 9. Migration / Deployment Safety

- New env vars documented in `.env.example`.
- Backward compatibility considered (mobile / web users on previous version).
- No breaking changes without bumping API version or migrating clients.
- Backfill scripts in `services/api/scripts/` if needed.

## 10. Forward-Compat & Architectural Debt

- Does this PR move us toward or away from the v2 roadmap items in [ROADMAP.md](ROADMAP.md)?
- Any debt introduced — abstractions deferred, tests skipped, magic numbers added? If yes, file a follow-up issue.

---

## Reviewer sign-off

- [ ] All 10 sections reviewed.
- [ ] `code_review_known_fixes.md` skimmed; no NF-NNN violations.
- [ ] CI green (lint + type-check + tests).
- [ ] `docs/CODEBASE_GUIDE.md` updated by this PR.
- [ ] Squash-merge intended.

**Verdict:** `PASS` / `NEEDS_CHANGES`.

Numbered findings if NEEDS_CHANGES — each tagged Critical / High / Medium / Low.
