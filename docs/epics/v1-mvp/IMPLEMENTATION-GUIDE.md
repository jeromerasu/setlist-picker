# IMPLEMENTATION-GUIDE — setlist-picker v1 frontend

This file is mandatory reading for any agent or human implementing a v1 screen.

## The source of truth is the prototype HTML

Every v1 screen has its layout, component hierarchy, and exact visual treatment defined in:

  `docs/design/FestApp.dc.html`

This is a 715-line static HTML prototype showing all 7 v1 screens. **Before implementing any screen, open this file, locate the section for the screen you're building, and mirror its structure exactly.**

DESIGN-TOKENS.md gives you the design *system* (colors, fonts, spacing, animations). The prototype HTML gives you the *layout* (which components compose into which screens, in which order, with which visual hierarchy). You need both.

## Screen → prototype section index

| Screen | Prototype section | Start line |
|---|---|---|
| Home / groups list | `<!-- SCREEN: GROUPS -->` | 36 |
| Create group | `<!-- SCREEN: CREATE -->` | 68 |
| Event picker (Choose festival) | `<!-- SCREEN: EVENT PICKER -->` | 96 |
| Join group | `<!-- SCREEN: JOIN -->` | 123 |
| Group detail | `<!-- SCREEN: GROUP (individual) -->` | 148 |
| Artist detail (cyber-retro divergence) | `<!-- SCREEN: ARTIST (cyber-retro) -->` | 236 |
| Schedule + All Stages (two tabs) | `<!-- SCREEN: SCHEDULE (calendar) -->` | 282 |

Key search strings inside each section:

- **Home:** `GROUPS` gradient title (l.40), `+ CREATE A GROUP` button (l.62), `Join a group` secondary button (l.63)
- **Event picker:** `isEventPicker` block (l.97); mono-letter event tiles in the event list
- **Join:** `Join a group` h1 (l.131), invite-code input
- **Group detail:** `Artists` heading (l.176), `Schedule` navigation button (l.166)
- **Artist:** VT323 hero name `{{ A.nameUpper }}` (l.245), `▸ TOP TRACKS` / `▸ SIMILAR` labels (l.258, l.270)
- **Schedule tabs:** `All Stages` tab (l.294), `Schedule` tab (l.295)
- **Schedule timeline:** `UP NEXT` label (l.366), `GOING` section label (l.370)

## Locked design decisions (June 2026)

These are decided — do not re-open them in tickets or ask about them:

1. **Schedule modes:** Both `Schedule` (per-day timeline) AND `All Stages` (grid) are v1 scope. Two tabs on the schedule screen.
2. **Going counts:** Group-aggregated, not event-wide. The BE endpoint counts picks across the active group's members only.
3. **Stage color palette:** 15 distinct hues (no repeats across Tomorrowland's 15 stages). Source: `HUES` array in `FestApp.dc.html` at l.614 (`this.HUES[i%this.HUES.length]`). Verify the token sheet has 15 entries before implementing any stage-color logic.
4. **Day picker:** Dropdown by default (not pills). Works for any day count; pills feel undersized on 3-day events.

## Rules

1. **Read DESIGN-TOKENS.md AND the prototype HTML before writing any code for a screen.** Not one or the other — both.
2. **Mirror the prototype's component composition.** If the prototype puts a day-picker dropdown above the schedule timeline, do not substitute a different layout because it "seems easier."
3. **Use exact tokens from DESIGN-TOKENS.md.** No invented colors, fonts, or spacing values. If a value isn't in the token sheet, ask before adding it.
4. **The cyber-retro artist screen is an intentional divergence** (see DESIGN-TOKENS § 5). Do not "fix" it to match the main palette.
5. **Stage colors come from the importer**, not from hand-coded constants in screen code. The HUES palette in DESIGN-TOKENS § 1.7 is the deterministic source; 15 entries, no duplicates.
6. **Day picker is a dropdown.** Do not implement day selection as pills or tabs.
7. **If the prototype is silent on a detail, ask before improvising.** Drift introduced by guesswork compounds across screens.

## Why this guide exists

In June 2026, multiple Code-session implementations of v1 screens (Schedule, Group Detail) drifted significantly from the prototype HTML because the prototype was gitignored at `.local-data/design/`. Implementers built from DESIGN-TOKENS.md alone, which gave them correct colors but invented layouts. The drift was discovered at integration time and required a realignment epic to fix. This guide is the preventive: prototype HTML is now committed at `docs/design/FestApp.dc.html`, and reading it before implementation is mandatory.
