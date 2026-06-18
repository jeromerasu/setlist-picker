# TASK-XXX-NNN — &lt;Short Title&gt;

> Fire-and-implement ticket template. Each ticket file is self-contained — an AI session or a human can read it, execute, and open a PR without needing additional context. Encode every design decision verbatim.

## Status

- [ ] Ready
- [ ] In progress
- [ ] In review
- [ ] Done

## Owner

TBD on pickup. Assign yourself by editing this line in the first PR commit.

## Repo + branch

**Repo:** `setlist-picker`
**Branch:** `feature/<descriptive-slug>` off `main`

## Dependencies

List of TASK-XXX-NNN IDs that must merge first. Use "none — can start in parallel" if independent.

## Scope

Two or three sentences describing what the ticket implements and what's intentionally out of scope.

## Files to touch

Tabular list. Implementer is constrained to these files unless the scope changes (which triggers a re-scope conversation).

| File | Purpose |
|---|---|
| `services/api/app/api/example.py` | Add the new endpoint handler. |
| `services/api/app/services/example_service.py` | Business logic for the endpoint. |
| `services/api/tests/test_example.py` | New test file. |
| `docs/CODEBASE_GUIDE.md` | Update the appropriate package section. |

## Acceptance criteria

Specific, testable behaviors. Each one should be verifiable in CI.

- [ ] Endpoint X returns 200 with the documented payload shape.
- [ ] Endpoint X returns 404 when the resource doesn't exist.
- [ ] Endpoint X is idempotent (calling it twice with the same input has no side-effect on the second call).
- [ ] `pytest`, `ruff check`, `mypy --strict` all green.
- [ ] `docs/CODEBASE_GUIDE.md` updated.

## Tests required

List specific test cases that must exist. Reviewer verifies each.

- `tests/test_example.py::test_happy_path`
- `tests/test_example.py::test_not_found_returns_404`
- `tests/test_example.py::test_idempotent`

## Hard rules

References to repo-wide invariants that apply to this ticket. Examples:

- snake_case wire JSON; Pydantic models honor PEP 8.
- No bare `except Exception` (NF-005 in `docs/code_review_known_fixes.md`).
- Structured logging on failure: `event=example.failed entity_id={x} reason={...}` (use `logger.exception(...)` for tracebacks).
- `'use client'` line 1 on any new interactive Next.js component (NF-001).
- Every PR updates `docs/CODEBASE_GUIDE.md`.

## Effort estimate

`XS` (≤ 1 h) / `S` (≤ ½ day) / `M` (≤ 1 day) / `L` (≤ 2 days). Right-sizing matters — large tickets should be split.

## Notes

Any design rationale, pointers to the spec section to read first, gotchas the implementer should know.

## Definition of done

- [ ] All acceptance criteria checked.
- [ ] Tests written and green.
- [ ] CI passing.
- [ ] PR opened with this ticket in the description.
- [ ] PR reviewed using `docs/code_review_template.md`.
- [ ] Squash-merged.
- [ ] `docs/CODEBASE_GUIDE.md` updated in this PR.
