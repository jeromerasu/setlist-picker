# FE-101 — Design tokens + reusable primitives (GlassCard, NeonGradientButton, AvatarStack, GradientText, StageDot)

**Wave:** 2
**Type:** FE
**Blocked by:** FE-100
**Blocks:** every Wave-3 FE ticket
**ADR references:** [DESIGN-TOKENS.md](./DESIGN-TOKENS.md)

## 1. Problem statement

Every Wave-3 screen uses the same handful of UI primitives — glass card, neon gradient button, avatar circle, gradient text, stage-color dot, glass-bottom-nav. Without them, each screen ticket would either duplicate code or block on this work. This ticket lands them once, with the design-tokens from DESIGN-TOKENS.md wired into NativeWind config.

## 2. Actual solution

1. Translate DESIGN-TOKENS.md into `apps/mobile/tailwind.config.ts` — `theme.extend.colors`, `theme.extend.fontFamily`, `theme.extend.borderRadius`, `theme.extend.spacing`, `theme.extend.boxShadow`.
2. `apps/mobile/src/theme/fonts.ts` — Expo font loader with all 5 families.
3. `apps/mobile/src/theme/gradients.ts` — the named gradients as `react-native-linear-gradient` config objects.
4. `apps/mobile/src/theme/motion.ts` — animation duration + reanimated helper functions.
5. `apps/mobile/src/components/` — primitives:
   - `GlassCard` — translucent surface with optional border + inset highlight.
   - `NeonGradientButton` — gradient-fill button, disabled state, optional shadow.
   - `OutlineButton` — secondary CTA.
   - `GradientText` — uses `@react-native-masked-view/masked-view` + `LinearGradient`.
   - `StageDot` — colored circle with optional glow halo.
   - `AvatarStack` — overlapping avatars with ring color.
   - `Avatar` — single circle with initials, color, optional border.
   - `GlassBottomNav` — the floating nav bar with `BlurView`.
   - `BackChip` — round 38px back button.
   - `PillTab` — chips for "All Artists / Day 1..." etc.
   - `SearchInput` — search field with icon.
   - `EmptyState` — illustration + heading + body + CTA.
6. Storybook-style screen at `apps/mobile/src/screens/__dev__/TokensGallery.tsx` — accessible in dev only, renders every primitive for visual verification.

Each primitive ships with snapshot tests + at least one interaction test (where applicable).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/tailwind.config.ts` | Token map. |
| `apps/mobile/src/theme/fonts.ts` | `useAppFonts()` hook + bundled `.ttf` registration. |
| `apps/mobile/src/theme/gradients.ts` | Named gradient configs. |
| `apps/mobile/src/theme/motion.ts` | Reanimated helpers. |
| `apps/mobile/src/theme/spacing.ts` | Exported spacing constants for non-Tailwind use. |
| `apps/mobile/src/components/GlassCard.tsx` | — |
| `apps/mobile/src/components/NeonGradientButton.tsx` | — |
| `apps/mobile/src/components/OutlineButton.tsx` | — |
| `apps/mobile/src/components/GradientText.tsx` | — |
| `apps/mobile/src/components/StageDot.tsx` | — |
| `apps/mobile/src/components/AvatarStack.tsx` | — |
| `apps/mobile/src/components/Avatar.tsx` | — |
| `apps/mobile/src/components/GlassBottomNav.tsx` | — |
| `apps/mobile/src/components/BackChip.tsx` | — |
| `apps/mobile/src/components/PillTab.tsx` | — |
| `apps/mobile/src/components/SearchInput.tsx` | — |
| `apps/mobile/src/components/EmptyState.tsx` | — |
| `apps/mobile/src/screens/__dev__/TokensGallery.tsx` | Dev gallery. |
| `apps/mobile/assets/fonts/*` | Orbitron, Playfair Display, Manrope, Space Mono, VT323 `.ttf` files. |
| `apps/mobile/__tests__/components/*.test.tsx` | One file per primitive. |
| `docs/CODEBASE_GUIDE.md` | Add primitives section. |

## 4. Method signatures / new APIs

```tsx
// GlassCard
interface GlassCardProps {
  variant?: "weak" | "med" | "strong";  // bg.surfaceWeak / Med / Strong
  border?: "default" | "subtle" | "strong";
  withInsetHighlight?: boolean;
  children: React.ReactNode;
  className?: string;
}

// NeonGradientButton
interface NeonGradientButtonProps {
  label: string;
  onPress: () => void;
  disabled?: boolean;
  size?: "md" | "lg";  // 48 / 52–54 px height
  fontFamily?: "Orbitron" | "Manrope";
  testID?: string;
}

// GradientText
interface GradientTextProps {
  children: string;
  gradient?: "title" | "schedule";  // matches gradients.title / scheduleCta
  font: "Orbitron" | "Manrope" | "PlayfairDisplay";
  weight: 700 | 800 | 900;
  size: number;
  letterSpacing?: number;
}

// Avatar
interface AvatarProps {
  initials: string;            // 1-2 chars
  color: string;               // #RRGGBB
  textColor?: string;          // optional override
  size?: 18 | 24 | 26 | 34 | 40;
  ringColor?: string;          // for AvatarStack
}

// AvatarStack
interface AvatarStackProps {
  members: Array<{ initials: string; color: string; textColor?: string }>;
  size?: 24 | 26;
  ringColor: string;           // e.g. tokens.bg.mid for default rings
  overlap?: number;            // default -7
  testID?: string;
}

// StageDot
interface StageDotProps {
  color: string;
  size?: 8 | 9 | 11;
  withGlow?: boolean;
}

// GlassBottomNav
interface NavItem {
  label: string;
  icon: React.ReactNode;
  onPress: () => void;
  isActive: boolean;
}

interface GlassBottomNavProps {
  items: NavItem[];
}

// PillTab
interface PillTabProps {
  label: string;
  active: boolean;
  onPress: () => void;
}

// EmptyState
interface EmptyStateProps {
  icon: React.ReactNode;
  title: string;
  body: string;
  cta?: { label: string; onPress: () => void };
}
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| AvatarStack default overlap | -7 px | DESIGN-TOKENS § 3.4. |
| AvatarStack default ring | `bg.mid` (`#140e34`) | Matches prototype `.stk{--ring:#140e34}`. |
| NeonGradientButton gradient | `gradients.title` (120deg pink→violet→cyan) | DESIGN-TOKENS § 1.6. |
| GlassBottomNav blur intensity | 50, `tint="dark"` | DESIGN-TOKENS § 4.2. |
| StageDot glow blur | `Math.round(size * 1.6)` halo View | DESIGN-TOKENS § 6 note 5. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Initials with emoji ("🎵") | Avatar renders the emoji (single grapheme). Font size scales to fit. |
| Avatar.initials length > 2 | Truncate to first 2 chars. |
| AvatarStack with 0 members | Renders nothing (View with width 0). |
| AvatarStack with > 8 members | Render first 4 + "+N" pill. (FE-005 uses this; primitive supports it.) |
| GradientText with empty children | Renders nothing. |
| NeonGradientButton disabled | Use `bg.surfaceWeak` + `border.disabled` + `text.placeholder` (matches prototype's `createBtnBg='transparent'` disabled state at line 91). |
| BlurView not supported (older Android) | `expo-blur` falls back to solid color; visual quality slightly degraded but functional. |
| Fonts not loaded yet | `useAppFonts()` returns `false` until ready; gallery shows a "Loading fonts…" placeholder. |
| Light theme | OQ-04 — defer; primitives render dark-mode only. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `__tests__/components/Avatar.test.tsx` | `renders_initials_and_color` | `render(<Avatar initials="JR" color="#a78bfa" />)`; assert text "JR" present; backgroundColor matches. |
| `__tests__/components/Avatar.test.tsx` | `truncates_long_initials` | "JRX" → renders "JR". |
| `__tests__/components/AvatarStack.test.tsx` | `renders_overlap_offsets` | Stack of 3 → 3 Views, marginLeft -7 for items 1+. |
| `__tests__/components/AvatarStack.test.tsx` | `caps_at_four_with_overflow_indicator` | 6 members → 4 avatars + "+2" pill. |
| `__tests__/components/GlassCard.test.tsx` | `variant_med_uses_correct_bg` | Variant `"med"` → backgroundColor `rgba(255,255,255,.07)`. |
| `__tests__/components/NeonGradientButton.test.tsx` | `disabled_state_does_not_call_onPress` | Press disabled → onPress not called. |
| `__tests__/components/NeonGradientButton.test.tsx` | `enabled_state_calls_onPress` | Press → onPress called. |
| `__tests__/components/GradientText.test.tsx` | `renders_text_via_masked_view` | Render → MaskedView descendant exists; child Text has the string. |
| `__tests__/components/StageDot.test.tsx` | `renders_dot_with_color` | `color="#ff4f9a"` → View backgroundColor matches. |
| `__tests__/components/StageDot.test.tsx` | `with_glow_renders_halo_view` | `withGlow=true` → halo View 1.6× size present. |
| `__tests__/components/GlassBottomNav.test.tsx` | `renders_n_items` | 3 items → 3 buttons. |
| `__tests__/components/GlassBottomNav.test.tsx` | `active_item_has_distinct_color` | Active item icon color matches `neon.purple` (`#a78bfa`); others muted. |
| `__tests__/components/PillTab.test.tsx` | `active_uses_purple_background` | active → bg `#a78bfa`. |
| `__tests__/components/EmptyState.test.tsx` | `renders_title_and_body` | Verify text content. |
| `__tests__/components/EmptyState.test.tsx` | `cta_optional_when_omitted` | No CTA prop → no button rendered. |

**Manual QA:**

1. Add `TokensGallery` to the bottom nav in dev only.
2. Visually verify every primitive against `.local-data/design/FestApp.dc.html` side-by-side.
3. Verify all 5 fonts load — switch the platform between iOS Simulator + Android emulator.
4. Toggle the device into reduced-motion: animations honor the system preference (FE-101 ships a `useReducedMotion` hook).
5. **Dark mode only.** Light theme is OQ-04 BACKLOG-001 — document any future divergence here.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| Cyber-retro artist-screen primitives (VT323 styling, scanline overlay) | FE-007 — keep local to that screen per OQ-02. |
| Storybook proper | Out — `TokensGallery` is sufficient. |
| Animation library (`moti` / etc.) | Not v1. `react-native-reanimated` 3 is enough. |
| Light theme primitives | BACKLOG-001. |
| Accessibility audit | Phase 6 polish — not in v1 unless test surfaces a glaring issue. Primitives include `accessibilityLabel` + minimum 44 px hit-target by default. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. Wave-3 screens become un-buildable until restored. Coordinate with whoever's mid-flight on FE-001..009.
