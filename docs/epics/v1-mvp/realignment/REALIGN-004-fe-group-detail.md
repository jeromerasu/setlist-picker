# REALIGN-004 — FE: Group detail screen rebuild

## Goal

Audit and rebuild the group detail screen to exactly match the prototype. The existing `GroupDetail.tsx` + `GroupDetailHeader.tsx` were built before the prototype was committed. This ticket restores fidelity on layout, typography, and interaction patterns.

## Source of truth

- Prototype: `docs/design/FestApp.dc.html` lines 148–235
- Design tokens: `docs/epics/v1-mvp/DESIGN-TOKENS.md`
- Implementation guide: `docs/epics/v1-mvp/IMPLEMENTATION-GUIDE.md`
- Existing files:
  - `apps/mobile/src/screens/groups/GroupDetail.tsx`
  - `apps/mobile/src/screens/groups/GroupDetailHeader.tsx`
  - `apps/mobile/src/screens/groups/ArtistRowAll.tsx`

## Full screen structure (prototype lines 148–235)

```
┌─────────────────────────────────────────┐
│ [back ‹]   [Group Name — gradient]  [DF] │
│ Tomorrowland 2026 — Weekend 2            │
│ Jul 24–26 · Boom, Belgium                │
│ [members stacked avatars]                │
│                                          │
│ [Schedule btn]  [Invite btn]             │
│ ✓ Invite copied … (toast)               │
│                                          │
│ [All Artists] [Day 1] [Day 2] ...        │
│                                          │
│ ┌──── Artist grid / day-stage list ────┐ │
│ │ [Vintage Culture card] [card] ...    │ │
│ └──────────────────────────────────────┘ │
└─────────────────────────────────────────┘
```

## Top bar (lines 153–163)

| Element | Prototype spec |
|---------|---------------|
| Back button | 38×38, `border-radius: 50%`, `background: rgba(255,255,255,.08)`, `‹` glyph, `font-size: 20px` |
| Group name | `font: 900 28px Orbitron; letter-spacing: .02em`; gradient text: `linear-gradient(120deg, #ff2d9b, #a64bff, #28e0ff)` with `-webkit-background-clip: text; background-clip: text; color: transparent` |
| User avatar | 40×40, `border-radius: 50%`, `background: linear-gradient(135deg, #a78bfa, #7b5cff)`, initials in `font: 800 14px Manrope` |

Row layout: `padding: 0 22px; display: flex; align-items: center; justify-content: space-between`.
Group name is `flex: 1; text-align: center` (centered between back and avatar).

## Event info block (lines 155–157)

- Event name: `font: 600 15px Manrope; color: #fff`
- Date range: `font: 500 13px Manrope; color: #a99fce`
- Location: `font: 500 13px Manrope; color: #a99fce`
- Container: `padding: 14px 22px 0; display: flex; flex-direction: column; gap: 4px`

## Members row (line 160)

- Avatar stack using `.stk` class: `display: flex; --ring: #140e34`; each avatar overlaps by -7px with 2px ring
- Avatar size: 30×30 (between `size.avatar.sm` 26px and `size.avatar.md` 34px — use the size visible in the prototype at line 160; defaults to 30px)
- Member count badge: shown as `+N` if members > visible cap (3 shown), `font: 700 12px Manrope; color: #a99fce`
- Row layout: `display: flex; align-items: center; gap: 10px; padding: 12px 22px 0`

## CTA row (lines 165–169)

Two buttons side-by-side, `display: flex; gap: 10px; padding: 14px 22px 0`:

**Schedule button** (line 166):
- `flex: 1; height: 46px; border-radius: 13px`
- `background: linear-gradient(120deg, #a64bff, #28e0ff)`
- `box-shadow: 0 8px 20px rgba(166,75,255,.4)`
- Calendar icon SVG (white, stroke-width 2) + `"Schedule"` text
- `font: 700 13px Manrope; color: #fff`
- Tapping navigates to Schedule screen (`schedTab: 'stages'`, `schedFilter: 'mine'`)

**Invite friends button** (line 165):
- `flex: 1; height: 46px; border-radius: 13px`
- `background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.16)`
- People-plus icon SVG (white) + `"Invite friends"` text
- `font: 700 13px Manrope`
- Tapping copies invite message to clipboard: `"Join my group on Setlist! Group code: {code}"`
- After copy, shows success toast (line 169):
  - `font: 600 12px Manrope; color: #28e0ff; animation: fadeIn .2s`
  - Text: `"✓ Invite copied — \"Join my group on Setlist! Group code: {code}\""`
  - Dismisses after 2600ms (token `motion.toastInvite`)

## Artist tabs (lines 170–175)

Horizontal scrollable tab strip: `"All Artists"`, `"Day 1"`, `"Day 2"`, `"Day 3"`, `"Day 4"` (day tabs shown for the event's day count).

Per tab:
- Active: `background: #a78bfa; border: transparent; color: #1a0c2e`
- Inactive: `background: rgba(255,255,255,.06); border: 1px solid rgba(255,255,255,.14); color: #cfc7e6`
- `font: 600 13px Manrope; border-radius: 99px; padding: 7px 16px`

## Artist content area

### "All Artists" tab (lines 176–230)

Header: `font: 800 20px Manrope`, text `"Artists"`, with count badge: `{n} total` in `font: 500 13px Manrope; color: #a99fce`.

Artist grid: `display: flex; flex-wrap: wrap; gap: 10px; padding: 0 22px`.

Per artist card:
- `width: calc(50% - 5px); border-radius: 16px; overflow: hidden; position: relative`
- Hero background: `this.HUES[i % 6]` — the 6-entry group-card gradient palette (DESIGN-TOKENS § 1.7). **Not stage colors.** The index `i` is the artist's sort position in the alphabetically sorted set list.
- Height: tall enough for the content (~90px minimum)
- Artist name: `font: 700 15px Manrope; color: #fff`
- Genre pills: up to 2 genres, `font: 500 10px 'Space Mono'; color: #fff; background: rgba(0,0,0,.25); border-radius: 99px; padding: 2px 7px`
- Stage dot: 8×8 circle, `background: {stage.color_hex}` (from REALIGN-001 API data)
- Stage name: `font: 500 11px Manrope; color: rgba(255,255,255,.8)`
- Tapping navigates to Artist screen

The 6 HUES for artist card backgrounds (verbatim from DESIGN-TOKENS § 1.7):
```
HUES[0] = linear-gradient(135deg, #ff4f9a, #7a1f6a)
HUES[1] = linear-gradient(135deg, #36c6ff, #1453d6)
HUES[2] = linear-gradient(135deg, #a06bff, #4b1fa8)
HUES[3] = linear-gradient(135deg, #2dd4bf, #0e7c66)
HUES[4] = linear-gradient(135deg, #ffd23f, #ff6a3d)
HUES[5] = linear-gradient(135deg, #ff2d9b, #5b1bd6)
```

### Day tab view (lines 615–625)

When a day tab is active, content switches to a **by-stage grouped list**, not a grid:

Per-stage group:
- Stage header: stage name in caps (`font: 700 12px Orbitron; letter-spacing: .08em`) + stage color dot
- Per-set row: artist name (`font: 600 13px Manrope`) + time range (`font: 500 11px 'Space Mono'; color: #9a8fc4`) + pick state indicator (filled/bordered square)

This is the `dayStageGroups` computation in the prototype (line 617). Implementer must derive this from the lineup data filtered by day label.

## API data flow

- `GET /api/groups/{invite_code}` (`GroupStateResponse`): provides group name, event, members, picks.
- `GET /api/events/{event_id}/lineup` (`EventLineupResponse`): provides stages (with `color_hex` after REALIGN-001), sets, artists.
- Artist genre data: if `GET /api/artists/{artist_id}` exists and returns genre info, use it; otherwise omit genres from the card (no placeholder text). Do not invent genres.

## States

| State | Condition | Renders |
|-------|-----------|---------|
| Loading | API in-flight | Spinner centered on canvas |
| Error | Any API error | Error text with retry option |
| Empty (all artists) | Event has 0 sets | `"No artists yet"` |
| Normal | Sets loaded | Full grid/list |
| Copied toast | User tapped invite | Toast visible for 2600ms |

## Acceptance criteria

- [ ] Group name renders as Orbitron 900 28px gradient text (pink→violet→cyan). Not Manrope.
- [ ] Schedule button uses the purple→cyan gradient with correct shadow.
- [ ] Artist cards use HUES[i % 6] gradients (the 6 group-card gradients), not solid colors.
- [ ] Stage color dots on artist cards use `color_hex` from the lineup API.
- [ ] Day tabs filter to sets for that day only, grouped by stage.
- [ ] Invite toast dismisses in exactly 2600ms.
- [ ] Member avatars overlap at -7px with 2px ring.
- [ ] `tsc --noEmit` passes. `npm test` passes.

## Out of scope

- Schedule screen (REALIGN-002, REALIGN-003).
- Typography audit of other screens (REALIGN-006).
- Artist detail screen (already implemented as FE-007 — do not touch cyber-retro divergence).
