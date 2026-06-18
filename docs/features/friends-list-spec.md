# Feature Spec — Friends List / Group View

**Status:** Approved scope; ready for ticket decomposition.
**Last updated:** 2026-06-18

## Problem

The group coordination story falls apart if you can't see who's in your group and where they're each planning to be. "Where is Sarah right now?" needs a 1-tap answer.

## Scope (v1)

- **Top-bar member avatars.** Every group member appears as a colored circle with their initials. Tap to see their full pick list.
- **Member colors.** Assigned at join time from a fixed palette of 12 distinct colors. Reused if > 12 members (the chance of two adjacent members getting the same color goes up; acceptable).
- **Per-set member dots.** Each set card on the calendar shows tiny colored dots for every group member planning to attend that set.
- **Member detail view.** Tapping a member's avatar opens a slide-over with their full pick list, grouped by day and stage.
- **"Right now" view.** A dedicated screen (or filter) that shows, for the current real-time moment, every group member and which set they're currently at. Empty members ("Sarah hasn't picked anything for now") shown explicitly.
- **Group rename.** The creator (or anyone — v1 is cooperative) can rename the group from "Friends 🎵" to whatever.

## Out of scope (v1)

- Kick / ban / role hierarchy.
- Direct messaging between members.
- Notifications when a friend updates their picks.
- Friend requests across groups.
- Member status ("at the bar", "headed to mainstage") beyond the inferred pick.

## Data model (existing — no new tables)

Reads from `member` + `pick`. No schema changes.

## API contract

- `GET /api/groups/{code}` — members + picks, polled every 5 s. Includes each member's assigned `color_hex`.
- `PATCH /api/groups/{code}` — rename the group (`{ name }`).
- `POST /api/groups/{code}/leave` — soft-remove the current member from the group (sets a `left_at` timestamp; doesn't delete picks for historical context).

## Tickets

| Ticket | Scope | Effort | Depends on |
|---|---|---|---|
| FE-FL-001 | Top-bar avatars — render member circles with assigned colors. Tap opens slide-over. | S | calendar FE-CAL-001 |
| FE-FL-002 | Member detail slide-over — full pick list grouped by day / stage. | S | FE-FL-001 |
| FE-FL-003 | Per-set member dots — tiny colored dots on each set card. | XS | FE-FL-001, calendar FE-CAL-001 |
| FE-FL-004 | "Right now" view — screen showing every member's currently-at set for the current clock. | S | FE-FL-002 |
| FE-FL-005 | Group rename UI — settings sheet, inline edit with optimistic update. | XS | FE-FL-001 |
| BE-FL-001 | `PATCH /api/groups/{code}` rename endpoint. | XS | none |
| BE-FL-002 | Member color assignment at join — picks the least-used color from the 12-palette. | XS | none |

Ticket files live in [`features/friends-list-tickets/`](friends-list-tickets/).

## Design integrity

- Match the rest of the app's visual language.
- Theme-aware via Tailwind tokens.
- Member colors must satisfy WCAG AA contrast against both light and dark backgrounds. Palette is chosen with this constraint.
- Initials always 1–2 chars, single-line truncation.

## Acceptance

- ✅ Members appear in the top-bar.
- ✅ Member colors assigned and persistent.
- ✅ Per-set dots render correctly.
- ✅ Member detail slide-over works.
- ✅ "Right now" view works at the current real-time clock.
- ✅ Group rename works end-to-end.
- ✅ All FE-FL-* and BE-FL-* tickets shipped.

## References
- [PRD.md § 5.3](../PRD.md)
- [features/calendar-spec.md](calendar-spec.md)
