# Contributing to Setlist Picker

Thanks for your interest in contributing. This is an open-source project and we welcome issues, PRs, and ideas from anyone.

## Getting started

1. **Fork** the repo and clone your fork locally.
2. Create a branch off `main`:
   ```bash
   git checkout -b feature/my-thing
   ```
3. Make your changes.
4. Run lint + type-check (see below).
5. Open a PR against `main` with a clear description of what you changed and why.

## Project layout

```
apps/web/       Next.js PWA (TypeScript)
services/api/   FastAPI backend (Python)
packages/types/ Shared TypeScript types (generated from OpenAPI)
data/           Lineup JSON seed data
docs/           PRD, architecture docs, ADRs, roadmap
```

## Code style

### TypeScript (apps/web, packages/)
- Formatter: Prettier (config at repo root when scaffold lands)
- Linter: ESLint
- Type checker: `tsc --noEmit`
- Run: `pnpm lint && pnpm type-check`

### Python (services/api/)
- Formatter + linter: Ruff (`ruff check . && ruff format --check .`)
- Type checker: mypy (`mypy --strict`)
- Runtime: Python 3.12+
- Package manager: `uv`

## Tests required

- Backend: pytest (add a test for any new endpoint or service logic)
- Frontend: Vitest / React Testing Library for any non-trivial component logic

CI runs lint + type-check on every PR. Tests are opt-in during the scaffold phase but required once the first feature ships.

## What to work on

Check [Issues](../../issues) and [ROADMAP.md](docs/ROADMAP.md) for open work. Good first issues are labelled `good first issue`.

If you want to work on something that isn't an open issue, open one first so we can discuss before you invest time.

## Lineup data

Do not submit actual festival lineup data in PRs. The repo uses example/placeholder data only (see `data/lineup-schema.example.json` for the schema). Each real festival's lineup requires a separate legal review before it can be included in the open-source repository — see [docs/PRD.md](docs/PRD.md) for details.

## Code of Conduct

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).
