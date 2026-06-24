# REALIGN-006 — FE: Typography audit across all screens

## Goal

Audit every v1 screen against the canonical typography tokens in `docs/epics/v1-mvp/DESIGN-TOKENS.md` § 2 and fix every deviation. This ticket addresses only font family, size, weight, and letter-spacing violations — not layout or color drift (those are covered in REALIGN-002 through REALIGN-004).

Typography drift is a correctness issue: the wrong font family (e.g., Manrope where Orbitron is specified) reads as visual noise to users familiar with the design system, and it signals to code reviewers that the token layer is not being used.

## Source of truth

- Token sheet: `docs/epics/v1-mvp/DESIGN-TOKENS.md` § 2 (Typography tokens — §§ 2.1–2.3)
- Prototype: `docs/design/FestApp.dc.html` (font values expressed as `style="font: ..."` inline rules)
- Existing screen files:
  - `apps/mobile/src/screens/groups/GroupsList.tsx`
  - `apps/mobile/src/screens/groups/GroupCard.tsx`
  - `apps/mobile/src/screens/groups/GroupDetail.tsx`
  - `apps/mobile/src/screens/groups/GroupDetailHeader.tsx`
  - `apps/mobile/src/screens/groups/CreateGroup.tsx`
  - `apps/mobile/src/screens/groups/JoinGroup.tsx`
  - `apps/mobile/src/screens/groups/EventPicker.tsx`
  - `apps/mobile/src/screens/artist/` (do NOT modify — cyber-retro divergence is intentional per DESIGN-TOKENS § 5)
  - `apps/mobile/src/screens/schedule/Schedule.tsx`
  - `apps/mobile/src/screens/schedule/Timeline.tsx`
  - `apps/mobile/src/screens/schedule/AllStagesGrid.tsx`
  - `apps/mobile/src/screens/schedule/DayMenu.tsx`
  - `apps/mobile/src/screens/profile/` (if present)
  - `apps/mobile/src/screens/snapshot/RightNowSnapshot.tsx`

## How to audit

For each screen file:

1. Grep for font family strings: `fontFamily:`, `font-family:`, and imported font constants.
2. For each text element, find the prototype equivalent and look up its `font:` rule.
3. Cross-reference against DESIGN-TOKENS § 2.2 (type scale table).
4. Fix any value that doesn't match the token.

## Token reference (critical violations to hunt for)

### Font families

| Context | Correct family | Common wrong family |
|---------|---------------|-------------------|
| `"GROUPS"` title, `"+ CREATE A GROUP"` button, day-stage headers (`"SHERWOOD COURT"`), status bar | Orbitron | Manrope |
| Section labels (`"GROUP NAME"`, `"EVENT"`), CTA button label | Manrope | Orbitron |
| Invite code input and display | Space Mono | Manrope |
| Per-set time labels in grid | Space Mono | Manrope |
| "UP NEXT" artist name, "Join a group" heading, empty-state heads | Playfair Display | Manrope |
| All body copy, meta rows, form inputs, tab labels | Manrope | (varies) |
| Artist screen only | VT323 + Space Mono | (do not touch) |

### Specific high-priority tokens

| Token | CSS rule | Common mistake |
|-------|---------|---------------|
| `text.title.xl` | `font: 900 30px Orbitron; letter-spacing: 0.03em` | Missing `letter-spacing`; wrong weight (700 or 800) |
| `text.title.lg` | `font: 900 28px Orbitron; letter-spacing: 0.02em` | Same |
| `text.title.sm` | `font: 700 19px Manrope` | Day picker button label uses Orbitron |
| `text.tab.orbitron` | `font: 700 12px Orbitron; letter-spacing: 0.08em` | Missing letter-spacing |
| `text.cta` | `font: 700 14px Orbitron; letter-spacing: 0.05em` | Missing letter-spacing |
| `text.section.serifLg` | `font: 700 30px 'Playfair Display'` | Manrope used for artist name in UP NEXT |
| `text.section.serifSm` | `font: 700 18px 'Playfair Display'` | Manrope used for set names in timeline |
| `text.mono.md` | `font: 700 12px 'Space Mono'; letter-spacing: 0.12em` | Missing letter-spacing on invite code display |
| `text.mono.sm` | `font: 500 12px 'Space Mono'` | Manrope used for time labels on timeline cards |
| `text.section.label` | `font: 700 12px Manrope; letter-spacing: 0.08em; text-transform: uppercase` | Missing `text-transform` or `letter-spacing` |

### Letter-spacing reference (from DESIGN-TOKENS § 2.3)

Any Orbitron usage without explicit `letterSpacing` is incorrect unless the token specifies none. The hierarchy:
- 0.18em — invite-code input (most aggressive)
- 0.12em — invite-code display chip
- 0.10em — UP NEXT label
- 0.08em — section labels, day-stage heads
- 0.05em — CTA "+ CREATE A GROUP"
- 0.03em — main title "GROUPS"
- 0.02em — group-detail title
- -0.01em — large title "Join a group" (slight tightening)

## What NOT to change

- **Artist screen files** (`apps/mobile/src/screens/artist/`): cyber-retro divergence (VT323 + Space Mono) is intentional. DESIGN-TOKENS § 5 documents this. Do not "normalize" it.
- Layout, colors, or spacing — those are REALIGN-002 through REALIGN-004 scope.
- Font *loading* (expo-font manifest in `apps/mobile/src/theme/fonts.ts`) — unless a font is missing from the manifest, which would be a REALIGN-001-style foundational issue, not a per-screen audit issue.

## Deliverable format

For each screen file audited, emit a one-line summary in the PR description:
- `GroupDetail.tsx`: ✓ no violations
- `Timeline.tsx`: fixed 3 violations (UP NEXT artist name Manrope→Playfair, time label Manrope→Space Mono, GOING label missing letter-spacing)

This makes the audit legible in code review.

## Acceptance criteria

- [ ] Every non-artist screen uses Orbitron only where DESIGN-TOKENS specifies Orbitron.
- [ ] Every non-artist screen uses Playfair Display only where DESIGN-TOKENS specifies Playfair Display.
- [ ] Every non-artist screen uses Space Mono only where DESIGN-TOKENS specifies Space Mono.
- [ ] `letterSpacing` is set on every Orbitron element that has a non-zero spec value.
- [ ] Artist screen files are untouched (verified via `git diff`).
- [ ] `tsc --noEmit` passes.
- [ ] `npm test` passes.
- [ ] PR description includes the per-file audit summary (violations found and fixed or "no violations").

## Out of scope

- Color corrections (REALIGN-002 / REALIGN-003 / REALIGN-004).
- Layout corrections (same).
- Font loading manifest (`fonts.ts`) changes.
- Adding new screens.
- Light-theme typography (BACKLOG-001).
