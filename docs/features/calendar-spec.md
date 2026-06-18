# Feature Spec — Calendar UI

**Status:** Approved scope; ready for ticket decomposition.
**Last updated:** 2026-06-18

## Problem

Users need to browse a multi-day, multi-stage lineup and pick the sets they want to see. Spreadsheet-style table views are unreadable on a phone. The lineup is naturally calendar-shaped (time × stage); render it that way.

## Scope (v1)

- **Day view** (default on mobile). Vertical time axis (top = morning, bottom = late night). Horizontal stage axis. Each set is a card spanning its `start`–`end` time in its `stage` column.
- **Week / agenda view** as an alternative. List-of-acts-per-day, easier to scroll on tiny screens.
- **Filter by stage** — toggle stages on/off. Cards in hidden stages hide. Filters persist across sessions in localStorage.
- **Filter by day** — top tabs for each day in the event.
- **"Now" indicator** — horizontal line at the current real-time clock; auto-scrolls into view on first load.
- **Pick toggle** — tap a set card to pick. Visual indication when picked (border + check icon).
- **Conflict highlighting** — sets you've picked that overlap with another picked set are flagged with a warning icon.
- **Group dots** — each set card shows tiny colored dots (one per group member planning to attend). Tapping the card opens the artist drill-down (separate feature).
- **Empty / loading states** — skeleton placeholders during initial fetch; "no sets on this day" empty state.

## Out of scope (v1)

- Drag-to-reschedule (sets are immovable — the lineup is the lineup).
- Personalized "recommended for you" view.
- Synchronized scroll across group members (your view ≠ their view; intentional).
- Print / share / export views.

## Design rationale

- **Day view is the default** because the venue experience is "what's happening today, where am I going next." Week view is for pre-event planning.
- **Vertical time axis** matches how people read schedules (top → bottom → "later"). Horizontal time axes are hard on small screens because long sets get truncated.
- **Color = stage** as the primary visual encoding; member dots are secondary visual encoding (small + at the edge of the card so they don't fight the stage color).

## Data model (existing — no new tables)

Reads from `event` / `stage` / `set` / `member` / `pick` per [ARCHITECTURE.md § Data model](../ARCHITECTURE.md).

## API contract

- `GET /api/events/{event_id}/lineup` — returns the full lineup (stages + days + sets). Cached client-side via service worker.
- `GET /api/groups/{code}` — returns members + picks. Polled every 5 s while tab is foregrounded.
- `POST /api/groups/{code}/picks` — `{ member_id, set_id }`. Idempotent.
- `DELETE /api/groups/{code}/picks/{set_id}` — `{ member_id }` in body.

## Tickets

Each ticket follows [`tasks/TASK_TEMPLATE.md`](../../tasks/TASK_TEMPLATE.md). Implementers can fire them sequentially or in parallel where dependencies allow.

| Ticket | Scope | Effort | Depends on |
|---|---|---|---|
| FE-CAL-001 | Day view skeleton — render time axis + stage columns + static set cards from `/lineup`. No pick interaction yet. | S | none |
| FE-CAL-002 | Pick toggle — tap card to add/remove pick. Optimistic update + rollback on error. | S | FE-CAL-001 |
| FE-CAL-003 | Week / agenda view — list-of-sets-per-day toggle. | S | FE-CAL-001 |
| FE-CAL-004 | Stage filter toggle — chips at top of day view; toggle stages on/off; persist in localStorage. | S | FE-CAL-001 |
| FE-CAL-005 | "Now" indicator — horizontal red line at current clock; auto-scroll on first load. | XS | FE-CAL-001 |
| FE-CAL-006 | Conflict highlighting — flag picked sets that overlap with another picked set. | S | FE-CAL-002 |
| FE-CAL-007 | Group dots on set cards — render colored dots for each member who's picked this set; depends on friends-list feature. | S | friends-list-spec FE-FL-001 |

Ticket files live in [`features/calendar-tickets/`](calendar-tickets/) — populate as you decompose.

## Design integrity

- Visual language must match the rest of the app (shadcn/ui primitives, Tailwind tokens, consistent radius / shadow / padding).
- Theme-aware: every color through Tailwind tokens, no hard-coded hex.
- 180–240 ms transitions on pick toggle, stage filter toggle, view switch.
- State-rich UI: every interactive element defines idle / pressed / loading / complete / disabled / error.
- Single-line truncation on artist names + stage labels on phone widths.
- Bottom-of-screen nav stays primary; calendar is the body content.

## Acceptance for the feature as a whole

- ✅ Day view renders the full lineup correctly.
- ✅ Week / agenda view available as a toggle.
- ✅ Pick toggle works online + offline (offline queue handled separately in offline-mode-spec).
- ✅ Stage + day filters work and persist.
- ✅ "Now" indicator visible and accurate.
- ✅ Conflict highlighting flags overlapping picked sets.
- ✅ Group dots render once friends-list-spec FE-FL-001 lands.
- ✅ Screenshots in both light and dark mode for every screen.
- ✅ All FE-CAL-* tickets shipped and merged.

## References

- [PRD.md § 5.2](../PRD.md)
- [ARCHITECTURE.md § API surface](../ARCHITECTURE.md)
- [features/friends-list-spec.md](friends-list-spec.md) for the group-dots integration
- [features/artist-drilldown-spec.md](artist-drilldown-spec.md) for the tap-card-opens-artist flow
