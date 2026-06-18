# ADR-002: Monorepo structure

## Status
Accepted

## Context
The repository hosts a web client (TypeScript), a backend service (Python), shared types (TypeScript), and design / data docs. It's a small project — one developer at v1, open to contributions — and operational simplicity matters more than perfection.

## Decision

Single repository. Layout:

```
setlist-picker/
├── apps/
│   └── web/                       # Next.js PWA (TypeScript)
├── services/
│   └── api/                       # FastAPI backend (Python)
├── packages/
│   └── types/                     # Shared TS types generated from OpenAPI
├── data/                          # Lineup JSON fixtures (schema example only — no real event data)
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md
│   ├── ROADMAP.md
│   ├── CODEBASE_GUIDE.md
│   ├── code_review_template.md
│   ├── code_review_known_fixes.md
│   ├── decisions/                 # ADRs
│   └── features/                  # Per-feature specs + ticket harnesses
├── tasks/
│   └── TASK_TEMPLATE.md
├── .github/                       # Workflows, PR template, issue templates
├── CLAUDE.md                      # Repo-specific hard rules
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE                        # MIT
└── turbo.json                     # Orchestrates TS apps + packages only
```

Turborepo orchestrates the TypeScript surfaces (`apps/web` + `packages/types`). The Python service (`services/api`) lives as a sibling with its own `pyproject.toml` + `uv` lockfile. Turborepo doesn't manage Python — that's intentional, the two language ecosystems stay decoupled.

## Rationale

1. **Code visibility.** Backend + frontend + shared types + docs all in one place. New contributors don't have to clone three repos to understand the system.
2. **Shared TypeScript types.** `packages/types` is generated from the OpenAPI schema FastAPI produces. Web client imports from there. Wire-contract drift becomes a build failure instead of a runtime bug.
3. **Atomic cross-cutting changes.** Adding a new endpoint: backend + types + frontend consumer can land in a single PR. No "frontend is broken because backend PR isn't merged" interlude.
4. **Single PR review surface.** One CI pipeline, one PR template, one set of merge conventions.

## Consequences

### Positive
- Easy onboarding (one clone, one project structure).
- Type sharing across web + types packages prevents wire-contract bugs.
- Atomic cross-stack PRs.

### Negative
- Mixed-language tooling at the root (`pnpm` for TS, `uv` for Python). Contributors need both installed.
- Build caching across languages is limited — Turborepo only caches TS work.
- Repo grows in size over time. Acceptable for the foreseeable future.

## References
- [ADR-001](ADR-001-tech-stack.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md)
