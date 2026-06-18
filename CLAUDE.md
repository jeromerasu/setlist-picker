# Claude Code Configuration — setlist-picker

## API Conventions

### JSON serialization: snake_case throughout

All FastAPI request and response models use snake_case field names (Pydantic v2 default). TypeScript interfaces on the frontend MUST use snake_case fields to match the wire format. Do not use camelCase for API payload types, even though it is idiomatic TS/JS.

Pattern — declare API payload types like:

```typescript
interface CreatePickPayload {
  group_code: string;
  set_id: string;
  member_name: string;
}
```

ESLint may warn about snake_case identifiers — disable that warning per-line or add a global rule for API payload interfaces.

> Cautionary tale (byb, 2026): sending camelCase keys to a snake_case-expecting API silently nulled non-required fields — no 400, just broken downstream data. `session_duration`, `experience_level`, etc. were ALL silently null.

## Hard Rules

- **Every task MUST pass `pytest` + `ruff check .` + `mypy --strict` (backend) and `npm test` + `tsc --noEmit` (frontend) before committing.** If checks fail, fix them — do not skip or suppress.
- **Every PR touching code MUST update `docs/CODEBASE_GUIDE.md`** if it adds, removes, or renames a class, endpoint, or significant module.
- **Feature branches + PRs + squash-merge only.** No direct pushes to main.
- **Keep tickets small and atomic.** Max 2–3 files per backend ticket; 1 page/component per frontend ticket. Broad tickets cause session hangs and lost work.
- **No bare `except Exception` in service-layer code.** Only specific recoverable exceptions are caught (`httpx` errors, `sqlalchemy.exc.*`, `TimeoutError`, `OSError`). Programming errors bubble. Top-level FastAPI exception handlers MAY broad-catch but MUST log the full traceback with `logger.exception(...)`.
- **All interactive Next.js client components require `'use client'` on line 1** — before comments, ESLint disables, or anything else. See NF-001 in `docs/code_review_known_fixes.md`.
- **FE `git add` in BE sessions MUST use explicit paths** (`git add docs/...`). `git add -A` / `git add .` in cross-repo sessions is FORBIDDEN.
- **Before creating an Alembic migration, run `ls services/api/alembic/versions/ | tail -5`** to find the latest version number. Never create migrations in parallel tasks — version conflicts corrupt Alembic history silently.

## Code Discipline

- **No assumptions.** Never invent method/class/type names, constants, or field names — verify in code first.
- **No hallucinated features.** Don't add product behavior unless explicitly asked.
- **Commit to a recommendation.** Don't flip-flop under pushback unless new information is introduced.
- **Structured logging is mandatory.** Every ticket must include structured logging for failures, fallbacks, and non-obvious decisions, with full context (entity IDs, action, full traceback via `logger.exception(...)`).

## Workflow

Use feature branches and pull requests for all changes. PRs require code review using `docs/code_review_template.md` and green CI before merging to main. Recurring traps are catalogued in `docs/code_review_known_fixes.md`. No direct pushes to main. Every PR is merged via **"Squash and merge"** — all feature-branch commits collapse into one commit on main.
