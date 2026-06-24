# REALIGN-003 — FE: All Stages grid sub-tab rebuild

## Goal

Audit and rebuild the **All Stages** sub-tab in the Schedule screen. This is the horizontal-scrolling time grid view showing all stages in parallel columns, with tappable set cards that cycle through going/maybe states. The existing `AllStagesGrid.tsx` was built before the prototype was committed and likely drifted.

## Source of truth

- Prototype: `docs/design/FestApp.dc.html` lines 298–339 (All Stages grid section)
- Design tokens: `docs/epics/v1-mvp/DESIGN-TOKENS.md` (§ 3.3 for grid sizing constants)
- Implementation guide: `docs/epics/v1-mvp/IMPLEMENTATION-GUIDE.md`
- Existing file: `apps/mobile/src/screens/schedule/AllStagesGrid.tsx`

## Layout overview

```
┌─────────────────────────────────────────────────────────┐
│ instruction row (hint + legend)                          │
│ search field                                             │
├─────────────────────────────────────────────────────────┤
│ [sticky] stage headers: [Mainstage] [Freedom] ...        │
│                                                          │
│ time grid (absolute-positioned set cards)                │
│  12:00 ──────────────────────────────────────────────── │
│  13:00 ── [Set card]   [Set card]                        │
│  ...                                                     │
└─────────────────────────────────────────────────────────┘
```

The grid container is horizontally scrollable. The left 48px is the time axis. Each stage column is 148px wide with a 10px gap.

## Scope

### Header area (lines 301–311)

**Instruction row:**
- Text: `font: 500 13px Manrope; color: #b6acd8`; leading `👆` emoji (font-size 14px); `"Tap once for going, tap again for maybe"`
- `display: flex; align-items: center; gap: 8px`

**Legend row** (`margin-top: 9px; display: flex; gap: 16px`):
- Maybe legend: 18×13 rect, `border-radius: 3px; border: 1.5px solid #a78bfa` + `"Maybe"` label; `font: 500 11px Manrope; color: #a99fce`
- Going legend: 18×13 rect, `border-radius: 3px; background: #a78bfa` (no border) + `"Going"` label; same font

**Search field** (`margin-top: 11px`):
- `height: 42px; border-radius: 11px; background: rgba(255,255,255,.07); border: 1px solid rgba(255,255,255,.12); padding: 0 13px`
- Search icon: SVG circle+line, `color: #8a82b8`
- Input: `font: 500 14px Manrope; color: #fff; background: none; placeholder: "Search artist or set…"; placeholder-color: #6a6592`

### Scrollable grid container (lines 313–337)

`position: absolute; top: 150px; left: 0; right: 0; bottom: 0; overflow: auto` (both axes).

Inner content width: `48 + numStages × 158` px. The extra 10px per stage (158 vs 148) accounts for the column gap.

#### Sticky stage headers (lines 316–320)

`position: sticky; top: 0; z-index: 6; display: flex; padding-left: 48px`
- Background fades into grid: `background: linear-gradient(#150e34, #150e34 70%, transparent)`
- Per-stage header tile: `width: 148px; flex: none; margin-right: 10px; height: 54px; border-radius: 12px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1); display: flex; flex-direction: column; align-items: center; justify-content: center`
  - Color dot: `width: 9px; height: 9px; border-radius: 50%; background: {stage.color_hex}; margin-bottom: 5px`
  - Stage name: `font: 700 13px Manrope; white-space: nowrap`

#### Time grid area (lines 322–336)

Container: `position: relative; height: {gridHeight}px; margin-top: 6px`

`gridHeight = (maxEnd - AX) × PXH + 20`

Where:
- `AX = floor(min(allSetStartHours for this day) - 0.5)` — earliest hour (with 30-min buffer)
- `PXH = 84` — pixels per hour (token `size.gridHourPx`)
- `maxEnd = max(allSetEndHours for this day, 24.5)`

**Hour lines** (line 323–325):
- For each integer hour `h` from `AX` to `ceil(maxEnd)`:
  - Horizontal rule: `position: absolute; left: 0; right: 0; top: {(h-AX)×84}px; border-top: 1px solid rgba(255,255,255,.06)`
  - Hour label: `position: absolute; left: 8px; top: -8px; font: 600 11px Manrope; color: #7a7298` — formatted as `"HH:MM"` (12h or 24h — match the format in the prototype's `fmt()` function)

**Set cards** (lines 326–334):

Each card is `position: absolute` within the time grid:
- `left = 48 + stageIndex × 158`
- `top = (set.startHour - AX) × 84`
- `width: 138px`
- `height = max((endHour - startHour) × 84 - 8, 46)`
- `border-radius: 13px; padding: 10px 11px; text-align: left; overflow: hidden; transition: .18s`

Three-state cycle (tap cycles none → going → maybe → none):

| State | `background` | `border` | `opacity` |
|-------|-------------|---------|----------|
| none | `rgba(255,255,255,.05)` | `1.5px solid rgba(255,255,255,.1)` | 1 (unless dimmed) |
| going | `{stage.color_hex}` | `1.5px solid {stage.color_hex}` | 1 |
| maybe | `transparent` | `1.5px solid {stage.color_hex}` | 1 |

Search dim: when a search query is active and the artist name does not include the query string (case-insensitive), `opacity: 0.25`.

Card contents:
- Artist name: `font: 700 14px Manrope; line-height: 1.05`
  - none/maybe: `color: #fff`
  - going: `color: #0d0818`
- Time label: `font: 500 11px 'Space Mono'; margin-top: 3px`
  - none/maybe: `color: #9a8fc4`
  - going: `color: rgba(13,8,24,.7)`
- Going avatar (shown only when state = going): `position: absolute; right: 8px; bottom: 8px`; 24×24 circle, `background: #a78bfa; border: 2px solid {stage.color_hex}`; user initials, `font: 800 9px Manrope; color: #1a0c2e`

## Time format

The prototype uses a 24-hour-style numeric format (e.g., `"14:30"` for 2:30 PM). The `fmt()` function in the prototype converts decimal hours: `Math.floor(h) + ":" + String(Math.floor((h%1)*60)).padStart(2,"0")`. Match this behavior exactly — do NOT use a 12-hour clock with AM/PM.

## Data requirements

**From API** (after REALIGN-001 lands):
- `GET /api/events/{event_id}/lineup` → `stages[].color_hex`, `stages[].sets[]`
- Set fields needed: `set_id`, `display_name`, `day_label`, `starts_at`, `ends_at`, `artists[0].name`
- Convert `starts_at`/`ends_at` (ISO timestamp) to decimal hours in the event's timezone for grid positioning.

**From local picks state** (React Query + optimistic):
- Current user's picks for this group: `{ [set_id]: 'going' | 'maybe' | undefined }`
- Tap action calls `POST /api/groups/{invite_code}/picks` with `state: "active"` (going) or a tombstone + re-pick for maybe. The exact client-side pick state machine is defined in the existing pick sync flow — REALIGN-003 reuses it unchanged.

## Acceptance criteria

- [ ] Grid columns scroll horizontally; stage headers remain sticky vertically.
- [ ] Grid sizes correctly: column width 148px, gap 10px, 84px per hour, 48px left axis.
- [ ] Hour lines appear at correct vertical positions with time labels (`"HH:MM"` format, 24h).
- [ ] Set cards positioned by `left = 48 + stageIdx × 158`, `top = (start - AX) × 84`.
- [ ] Tapping a card cycles: none → going → maybe → none (three taps back to start).
- [ ] Going card: stage-color background, dark text, avatar in bottom-right.
- [ ] Maybe card: transparent background, stage-color border, white text.
- [ ] Stage dots in sticky header use `color_hex` from API (not hardcoded).
- [ ] Search field dims non-matching cards to `opacity: 0.25`.
- [ ] Legend shows correct going (filled) and maybe (bordered) chips.
- [ ] Instruction row shows the tap hint with `👆` emoji.
- [ ] `tsc --noEmit` passes. `npm test` passes.

## Out of scope

- Timeline sub-tab (REALIGN-002).
- Group detail screen (REALIGN-004).
- Group-aggregated picks endpoint (REALIGN-005).
- Typography audit for other screens (REALIGN-006).
