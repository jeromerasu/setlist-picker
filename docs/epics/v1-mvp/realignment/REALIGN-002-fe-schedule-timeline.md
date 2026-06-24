# REALIGN-002 — FE: Schedule screen — timeline sub-tab rebuild

## Goal

Audit and rebuild the **Schedule** sub-tab (the timeline / per-set list view) in the Schedule screen to exactly match the prototype. The existing `Schedule.tsx` + `Timeline.tsx` were built before the prototype was committed and may have drifted. This ticket restores fidelity: correct layout, exact tokens, correct state machine.

## Source of truth

- Prototype: `docs/design/FestApp.dc.html`
  - Top bar + sub-tabs: lines 282–296
  - Schedule (timeline) tab content: lines 341–424
  - Day dropdown menu: lines 426–438
  - Group filter bottom sheet: lines 440–457
- Design tokens: `docs/epics/v1-mvp/DESIGN-TOKENS.md`
- Implementation guide: `docs/epics/v1-mvp/IMPLEMENTATION-GUIDE.md` (mandatory pre-read)
- Existing files to audit/rewrite:
  - `apps/mobile/src/screens/schedule/Schedule.tsx` — top bar, tab switcher, day state
  - `apps/mobile/src/screens/schedule/Timeline.tsx` — timeline list content
  - `apps/mobile/src/screens/schedule/DayMenu.tsx` — dropdown overlay

## Scope

Audit the following elements against the prototype and fix every deviation. Preserve any element that already matches exactly — this is an audit+fix, not a blank-slate rewrite.

### Top bar (line 286–290)

| Element | Prototype spec |
|---------|---------------|
| Back button | 40×40, `border-radius: 50%`, `background: rgba(255,255,255,.08)`, `font-size: 19px`, `‹` glyph |
| Day picker button | Center; `font: 700 19px Manrope`; label `"Day {n}"` + caret `▼`/`▲`; `color: #a78bfa` for caret |
| Right share icon | 40×40, `background: rgba(255,255,255,.08)`, upload SVG |

### Sub-tabs (lines 293–296)

Two tabs: **All Stages** (left) and **Schedule** (right). Each tab:
- `flex: 1`, `padding-bottom: 11px`, centered content with icon + label
- `font: 600 15px Manrope`
- Active: `color: #a78bfa`, `border-bottom: 2px solid #a78bfa`
- Inactive: `color: #8a82b8`, `border-bottom: 2px solid transparent`
- All Stages icon: 4-square grid SVG (filled)
- Schedule icon: calendar SVG (stroked)

### Schedule sub-tab filter chips (lines 347–349)

Two chip buttons rendered below the tabs:
- **Group chip**: people icon + `"Group"` + separator `|` + small caret `⌄`; `font: 700 14px Manrope`. Active: `background: #cdb4fe`, `border: transparent`, `color: #1a0c2e`. Inactive: `background: rgba(255,255,255,.06)`, `border: 1px solid rgba(255,255,255,.16)`, `color: #fff`. Tapping opens the group filter sheet.
- **Mine chip**: star `★` + `"Mine"`; same active/inactive style as Group. Tapping toggles mine filter on/off (if already active, returns to `filterNone`).
- Chips sit in a row with `gap: 10px` at `padding: 12px 22px 4px`.

### Filter states

Three mutually exclusive states: `filterNone`, `filterMineActive`, `filterGroupActive`.

**filterNone empty state (lines 354–360):**
- Center-padded `padding: 90px 30px 0`
- 64×64 circle icon ring: `border: 2px solid rgba(255,255,255,.18)`, filter SVG inside
- Title: `font: 700 22px 'Playfair Display'`, `color: #cfc7e6`, text `"No Filter Selected"`
- Subtitle: `font: 500 14px Manrope`, `color: #8a82b8`, `"Tap Mine or Group above\nto see sets"`

**filterMineActive — has picks (lines 362–387):**

UP NEXT card (line 364–369):
- `border-radius: 18px`, `padding: 15px 16px`, `background: rgba(255,255,255,.05)`, `border: 1px solid rgba(255,255,255,.1)`, `position: relative`, `overflow: hidden`
- Left-side gradient bar: `position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: linear-gradient(#ff2d9b, #a64bff)`
- Label row: `font: 700 11px Manrope; letter-spacing: .1em; color: #ff8ad6` + `"UP NEXT"` + inline time string (`color: #8a82b8; font-weight: 500`)
- Artist name: `font: 700 30px 'Playfair Display'`, `margin-top: 4px`
- Meta row: stage color dot (8×8, `border-radius: 50%`) + stage name + time range; `font: 500 13px Manrope; color: #c8b9ff`

GOING header (line 370):
- Checkmark circle: 18×18, `background: #a78bfa`, contains white checkmark SVG (`stroke-width: 3`)
- Label: `font: 800 13px Manrope; letter-spacing: .06em; color: #a78bfa`, text `"GOING"`
- Count badge: pushed to right; 26×26 circle, `background: rgba(255,255,255,.08)`, `font: 700 12px Manrope; color: #a99fce`

Per-set timeline cards (lines 372–385):
- Row layout: `display: flex; gap: 14px; margin-bottom: 16px`
- Time column: 62px wide; `font: 700 15px Manrope` (start); `font: 500 12px Manrope; color: #8a82b8` (end)
- Dot + connector column: 14px wide; dot is 11×11 `border-radius: 50%`, stage color + matching glow `box-shadow: 0 0 8px {color}`; vertical connector line `width: 1px; background: rgba(255,255,255,.12)`
- Card: `flex: 1; border-radius: 16px; padding: 13px 14px; background: rgba(255,255,255,.05); border: 1px solid rgba(255,255,255,.1)`
  - Remove (✕) button: `position: absolute; top: 11px; right: 11px`; 24×24, `background: rgba(255,255,255,.08)`, `color: #a99fce`
  - Artist name: `font: 700 18px 'Playfair Display'` (tappable, opens artist screen)
  - Stage meta: stage dot 8×8 + stage name; `font: 500 13px Manrope; color: #b6acd8`
  - Going label: avatar + `font: 500 12px Manrope; color: #a99fce`

**filterMineActive — no picks (lines 389–395):**
- Emoji `🎟️` (font-size: 40px), centered
- Title: `font: 700 22px 'Playfair Display'; color: #cfc7e6`, `"Pick your first set"`
- Subtitle: `font: 500 14px Manrope; color: #8a82b8`

**filterGroupActive — has picks (lines 400–411):**
- Same timeline card structure as Mine, but no UP NEXT card and no remove button
- Avatar stack instead of single avatar: `stk` class (overlapping -7px, 2px ring `#1c143a`)
- Going label: `"{n} going"`

**filterGroupActive — no picks (lines 414–420):**
- Group silhouette SVG, `color: #5a5278`
- Title: `"No Group Sets Yet"`, same tokens as filterNone
- Subtitle: `"When group members mark sets,\nthey'll appear here"`

### Day dropdown menu (lines 426–438)

Overlay: `position: absolute; inset: 0; z-index: 40; background: rgba(0,0,0,.4); animation: fadeIn .15s` — tapping closes menu.

Card: `position: absolute; top: 84px; left: 50%; transform: translateX(-50%); width: 230px; border-radius: 18px; background: #241a44; border: 1px solid rgba(255,255,255,.12); box-shadow: 0 16px 40px rgba(0,0,0,.5); animation: fadeIn .15s`

Each day row:
- `padding: 14px 18px; border-bottom: 1px solid rgba(255,255,255,.06)`
- Number circle: 30×30, `border-radius: 50%`; active: `background: #a78bfa; color: #1a0c2e`; inactive: `background: rgba(255,255,255,.1); color: #a99fce`
- Day label: `font: 600 15px Manrope`; active: `color: #fff`; inactive: `color: #a99fce`
- Active check: `color: #a78bfa`, `✓` glyph

### Group filter sheet (lines 440–457)

Bottom sheet with `sheetUp .25s` animation:
- Backdrop: `background: rgba(0,0,0,.5)`, closes on tap
- Sheet: `border-radius: 24px 24px 0 0; background: #1a1232; padding: 14px 22px 30px`
- Handle: 40×5 pill, `background: rgba(255,255,255,.2)`, centered, `margin-bottom: 16px`
- Header row: `font: 800 20px Manrope` title `"Filter Group"` + `"Done"` button (`font: 700 15px Manrope; background: rgba(255,255,255,.1); padding: 7px 16px; border-radius: 99px`)
- Divider row: `"Clear All"` (`font: 700 14px Manrope; color: #a78bfa`) + count label (`font: 500 13px Manrope; color: #8a82b8`)
- Member rows: 34×34 avatar + `font: 600 15px Manrope` name + 24×24 checkbox (`border-radius: 7px`, `border: 1.5px solid`)
  - Checked checkbox: `background: #a78bfa; border: #a78bfa`; white checkmark SVG `stroke-width: 3`
  - Unchecked: `background: transparent; border: rgba(255,255,255,.22)`

## API contract (no new endpoints needed for this ticket)

This ticket consumes `GET /api/groups/{invite_code}` (`GroupStateResponse`) which already returns `picks: list[PickSummary]` with `state` and `set_id`. Group filter ("Group" chip) requires member-aggregated data — consume the existing `picks` list, correlating by `member_id` from the `members` array already in `GroupStateResponse`.

> **Prerequisite**: REALIGN-001 must land first so stages have `color_hex`. Use `color_hex` from `GET /api/events/{event_id}/lineup` (cached after the first group load) for stage dot colors on timeline cards.

## States that must render correctly

| State | Condition | Renders |
|-------|-----------|---------|
| filterNone | No chip active | Empty-state with filter icon |
| filterMine / hasPicks | Mine active, `>0` picks today | UP NEXT + GOING list |
| filterMine / noPicks | Mine active, `0` picks today | Ticket emoji empty state |
| filterGroup / hasGroupSets | Group active, `>0` picks across members | Timeline with avatar stacks |
| filterGroup / noGroupSets | Group active, `0` picks across members | Group silhouette empty state |
| dayMenuOpen | Dropdown toggled | Overlay + floating card |
| filterSheetOpen | Group chip tapped | Bottom sheet |

## Acceptance criteria

- [ ] Renders at 390-wide viewport with no layout overflow.
- [ ] Day picker is a dropdown (`DayMenu.tsx` overlay), NOT pills or tabs.
- [ ] Sub-tab active state uses exact token: `#a78bfa` underline, 2px.
- [ ] UP NEXT card has the left-side gradient bar (`#ff2d9b → #a64bff`).
- [ ] Stage color dots use `color_hex` from the API (not hardcoded values).
- [ ] `fadeIn .25s` / `sheetUp .25s` animations on day menu / filter sheet.
- [ ] All typography matches DESIGN-TOKENS § 2 exactly (no invented font sizes or weights).
- [ ] `tsc --noEmit` passes.
- [ ] `npm test` passes.

## Out of scope

- All Stages grid tab (REALIGN-003).
- Group detail screen (REALIGN-004).
- BE changes (REALIGN-001 handles color_hex, REALIGN-005 handles group-aggregated endpoint if needed).
- Light theme.
