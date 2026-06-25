# Coordination message template — setlist-picker

The exact text Dispatch (or any human runner) should send to a Claude Code implementation session when firing a task. This file is the source of truth; don't re-derive the language.

## When to use this template

- Single-task fire: send this template pointing at one task file.
- Multi-task wave fire (chained): send this template once per step in the chain.
- Re-fire after a session restart: the EPIC + task files are committed; the new session reads them and continues with the same harnesses.

## Template

```
Read docs/<wave>/EPIC.md and tasks/<TASK>.md IN FULL before writing code.
Execute strictly per the task — Files to touch table is a hard contract.
Verbatim test names from the "Tests required" list — exact method names.
Acceptance criteria are verbatim — meet each one or surface the blocker.
If ANY spec detail feels ambiguous, STOP and surface as a re-scope conversation. Don't guess.
Report back per the task's Definition of Done. Deviations must be called out explicitly.
```

For single-task fires (no EPIC):

```
Read tasks/<TASK>.md IN FULL before writing code.
Execute strictly per the task — Files to touch table is a hard contract.
Verbatim test names from the "Tests required" list — exact method names.
Acceptance criteria are verbatim — meet each one or surface the blocker.
If ANY spec detail feels ambiguous, STOP and surface as a re-scope conversation. Don't guess.
Report back per the task's Definition of Done. Deviations must be called out explicitly.
```

## What this template enforces

| Rule | Enforced by line |
|---|---|
| Agent MUST read spec before code | "Read … IN FULL before writing code" |
| No invented file scope | "Files to touch table is a hard contract" |
| No invented test names | "Verbatim test names" |
| No silent acceptance-criterion drift | "Acceptance criteria are verbatim" |
| No guessing on ambiguity | "STOP and surface as a re-scope conversation" |
| Audit trail on deviations | "Deviations must be called out explicitly" |
| Mechanical DOD check | "Report back per the task's Definition of Done" |

## What this template does NOT do

- Duplicate acceptance criteria, hard rules, file paths, or test names — those live in the task file.
- Repeat the validation gate (pytest + ruff + mypy --strict for BE; npm test + tsc --noEmit for FE) — those are in `docs/WORKFLOW.md` and the per-task DOD.
- Re-state the wave-level goal, festival-day projections, or LWW semantics — those are in the EPIC.

The agent gets MAXIMUM grounding from the committed EPIC + task. This template is the HARNESSING that keeps the agent strict.

## What changes per task

Only one thing: the path to the EPIC + task file. Everything else is identical across tasks.

## Anti-patterns (don't do this)

- ❌ Pasting acceptance criteria back into the send_message. The task file is the source of truth; duplicating risks drift between message and file.
- ❌ Adding scope ("oh and also fix this other thing while you're in there"). Surface as a separate task; don't expand mid-execution.
- ❌ Skipping the "STOP on ambiguity" line. That line is load-bearing — it's why the agent doesn't hallucinate.
- ❌ Loosening LWW semantics ("just to handle this edge case"). The `state_clock_ms` inequality direction is canonical — don't touch it without re-scope.
- ❌ Sending the same message twice with different content. The session will get confused.

## Companion docs

- `docs/WORKFLOW.md` — the overall workflow (3 artifacts per multi-task wave; v1 integration branch model; Render auto-deploy)
- `tasks/TASK_TEMPLATE.md` — the per-task structure
- Memory: `feedback_epic_ticket_workflow` — Dispatch-side memory of this pattern
