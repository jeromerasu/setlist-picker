# DESIGN-TOKENS — setlist-picker v1 (Cosmic-Neon)

Tokens extracted from the chosen prototype `docs/design/FestApp.dc.html` (715 lines, 7 screens). Every value here is grepped from that file — no invented values. Where a value depends on theme (light vs dark), v1 is **dark only** (per EPIC OQ-04). Light theme is `BACKLOG-001-light-theme.md`.

Implementer reads this file and writes:

- `apps/mobile/tailwind.config.ts` — token map (NativeWind consumes it).
- `apps/mobile/src/theme/tokens.ts` — exported TypeScript constants for non-Tailwind use (`react-native-linear-gradient` stops, animation timings, raw shadow strings).
- `apps/mobile/src/theme/fonts.ts` — Expo font loading manifest.

## 1. Color tokens

### 1.1 Neutrals (the cosmic backdrop)

| Token | Hex | Used in prototype | Notes |
|---|---|---|---|
| `bg.canvas` | `#0a0712` | `body { background: #0a0712 }` (line 16) | App background outside the device frame. |
| `bg.deep` | `#08060f` | `radial-gradient(... #08060f 100%)` (line 29) | Outermost stop of the device-frame radial gradient. |
| `bg.mid` | `#150e34` | `radial-gradient(... #150e34 50%)` (line 29); day-menu and stage-header backgrounds. | Reads as "deep purple-black." |
| `bg.high` | `#1a1232` | Filter sheet (line 443). | Sheet / modal lift over the canvas. |
| `bg.elevated` | `#241a44` | Day menu (line 429). | Above-canvas surface. |
| `bg.surfaceWeak` | `rgba(255,255,255,.05)` | Card backgrounds (multiple). | Translucent surface — relies on cosmic backdrop for tint. |
| `bg.surfaceMed` | `rgba(255,255,255,.07)` | Search input row (line 104), invite button (line 165). | One step brighter. |
| `bg.surfaceStrong` | `rgba(255,255,255,.08)` | Back-button circle (line 72). | Used for back / icon buttons. |
| `bg.surfaceTab` | `rgba(255,255,255,.06)` | Inactive artist tabs (line 610). | Specific to pill tabs. |
| `bg.glassNav` | `rgba(18,12,40,.72)` | Bottom nav (line 463). | Pair with `backdrop-filter: blur(18px)`. |

### 1.2 Brand neon palette

| Token | Hex | Prototype usage |
|---|---|---|
| `neon.pink` | `#ff2d9b` | Title gradient start; create-button gradient start; LWW timeline accent. |
| `neon.violet` | `#a64bff` | Title gradient middle; create-button middle. |
| `neon.cyan` | `#28e0ff` | Title gradient end; create-button end. |
| `neon.purple` | `#a78bfa` | Day-menu active background; bottom-nav active icon; primary-tag inactive border. |
| `neon.purpleDeep` | `#7b5cff` | Top-right avatar gradient end. |
| `neon.violetSat` | `#5b1bd6` | Card hero gradient end. |
| `neon.skyDeep` | `#1453d6` | "Bass Heads" card hero gradient end. |
| `neon.lilac` | `#cdb4fe` | Active "Group" / "Mine" filter chip background. |
| `neon.lavenderDim` | `#b6acd8` | Body text on dark surfaces (e.g. event detail rows). |
| `neon.violetText` | `#9b8cff` | Section-label text ("GROUP NAME"). |
| `neon.violetAvatar` | `#a78bfa` | "DF" current-user avatar background. |

### 1.3 Stage palette (used in schedule grid)

Full 15-entry palette (REALIGN-001). Assigned by the importer at insert time via `display_order % 15`; defined as `_STAGE_COLORS` in `lineup_import_service.py`. Index order is canonical — do not reorder.

| Index | Token / source | Hex |
|-------|---------------|-----|
| 0 | `stage.sherwood` | `#ff4f9a` |
| 1 | `stage.tripolee` | `#36c6ff` |
| 2 | `stage.ranch` | `#a06bff` |
| 3 | `stage.cosmic` | `#2dd4bf` |
| 4 | HUES[4] amber start | `#ffd23f` |
| 5 | HUES[4] orange end | `#ff6a3d` |
| 6 | `neon.pink` | `#ff2d9b` |
| 7 | `neon.cyan` | `#28e0ff` |
| 8 | `neon.purple` | `#a78bfa` |
| 9 | `neon.purpleDeep` | `#7b5cff` |
| 10 | HUES[3] forest end | `#0e7c66` |
| 11 | `neon.violetSat` | `#5b1bd6` |
| 12 | `text.daySectionAccent` | `#ff8ad6` |
| 13 | `neon.skyDeep` | `#1453d6` |
| 14 | `neon.lilac` | `#cdb4fe` |

The 4 original seed values (indices 0–3) appear hardcoded in the prototype for Lost Lands stages. Indices 4–14 are drawn from § 1.1 / § 1.2 to ensure visual distinctness across all 15 Tomorrowland stages.

### 1.4 Text colors

| Token | Hex | Use |
|---|---|---|
| `text.primary` | `#ffffff` | Headlines on dark surface. |
| `text.secondary` | `#a99fce` | Card subtitles, meta rows. |
| `text.tertiary` | `#8a82b8` | Inactive tab labels, placeholder hints. |
| `text.muted` | `#7a7298` | Time-axis labels in grid view. |
| `text.placeholder` | `#6a6592` | Input placeholders (`input::placeholder` rule, line 25). |
| `text.invertedDark` | `#1a0c2e` | On bright neon backgrounds (active chip text, gradient avatar `DF`). |
| `text.error` | `#ff6a8a` | Join-error message (line 138). |
| `text.success` | `#28e0ff` | "Invite copied" toast (line 169). |
| `text.eventName` | `#cfc7e6` | Empty-state headline ("No Filter Selected"). |
| `text.daySectionAccent` | `#ff8ad6` | "UP NEXT" label. |
| `text.mineSection` | `#a78bfa` | "GOING" section label. |
| `text.iconAccent` | `#c8b9ff` | Invite-code monospace highlight. |

### 1.5 Border / divider tokens

| Token | Value | Use |
|---|---|---|
| `border.weak` | `rgba(255,255,255,.06)` | Hour-line divider in grid view. |
| `border.subtle` | `rgba(255,255,255,.08)` | Top-bar separator, day-menu row divider. |
| `border.default` | `rgba(255,255,255,.1)` | Card borders. |
| `border.mid` | `rgba(255,255,255,.12)` | Bottom-nav border. |
| `border.medium` | `rgba(255,255,255,.13)` | Search input border. |
| `border.strong` | `rgba(255,255,255,.14)` | Input borders. |
| `border.high` | `rgba(255,255,255,.16)` | "Invite friends" button. |
| `border.input` | `rgba(255,255,255,.18)` | Empty-state ring around the icon. |
| `border.disabled` | `rgba(255,255,255,.22)` | Disabled CTA outline. |
| `border.pickedAccent` | `rgba(255,45,155,.5)` | Picked-set card border. |
| `border.appleAcid` | `#00e5ff` | Artist-screen back button border. |
| `border.appleHot` | `#ff00a8` | Artist-screen "friends going" pill border. |

### 1.6 Gradient stops (used as raw strings — copy verbatim)

| Token | Value | Use |
|---|---|---|
| `gradient.title` | `linear-gradient(120deg, #ff2d9b, #a64bff, #28e0ff)` | "GROUPS" title; group-detail title; create-button when active. |
| `gradient.titleBgClip` | same — applied with `-webkit-background-clip: text; background-clip: text; color: transparent` | The neon-text effect. |
| `gradient.scheduleCta` | `linear-gradient(120deg, #a64bff, #28e0ff)` | "Schedule" button on group detail (line 166). |
| `gradient.deviceFrame` | `radial-gradient(125% 70% at 50% -6%, #34165e 0%, #150e34 50%, #08060f 100%)` | Device-frame backdrop (line 29). |
| `gradient.canvasOuter` | `radial-gradient(circle at 50% 0%, #1a1038, #0a0712)` | Surrounding page background. |
| `gradient.fadeBottom` | `linear-gradient(to top, rgba(8,6,15,.55), transparent 70%)` | Group-card bottom-fade overlay. |
| `gradient.heroFadeIn` | `linear-gradient(to bottom, transparent 42%, #0d0818)` | Artist-screen hero fade (line 242). |
| `gradient.timelineLwwBar` | `linear-gradient(#ff2d9b, #a64bff)` | "Up Next" left-side bar. |
| `gradient.pickedSetCard` | `linear-gradient(135deg, rgba(255,45,155,.22), rgba(40,224,255,.12))` | Per-day picked set card background. |
| `gradient.userAvatar` | `linear-gradient(135deg, #a78bfa, #7b5cff)` | Top-right user-avatar circle. |
| `gradient.pickedCheck` | `linear-gradient(135deg, #ff2d9b, #28e0ff)` | Picked-set checkmark circle. |

### 1.7 Group-card hero palette (`HUES[]` — line 537)

Used to assign a hero gradient to a newly-created group's home card. Rotation: `(group_position) % 6`. Values are gradient strings:

```
HUES[0] = linear-gradient(135deg, #ff4f9a, #7a1f6a)    // bright pink → deep magenta
HUES[1] = linear-gradient(135deg, #36c6ff, #1453d6)    // cyan → deep blue
HUES[2] = linear-gradient(135deg, #a06bff, #4b1fa8)    // soft purple → deep purple
HUES[3] = linear-gradient(135deg, #2dd4bf, #0e7c66)    // teal → forest
HUES[4] = linear-gradient(135deg, #ffd23f, #ff6a3d)    // amber → orange
HUES[5] = linear-gradient(135deg, #ff2d9b, #5b1bd6)    // hot pink → indigo
```

### 1.8 Cyber-retro artist-screen accents (OQ-02 — kept intentionally divergent)

Used **only** on FE-007 (artist detail). Do not promote to the Cosmic-Neon main palette.

| Token | Hex | Use |
|---|---|---|
| `cyber.bg` | `#0d0818` | Artist-screen base background. |
| `cyber.acid` | `#00e5ff` | Section heads ("▸ TOP TRACKS"), back-button border. |
| `cyber.hot` | `#ff00a8` | "Friends going" pill border, hero radial. |
| `cyber.yellow` | `#f5ff00` | Artist name VT323 fill. |
| `cyber.yellowDim` | `#c8d000` | Genre-pill border (third color). |
| `cyber.text` | `#ffb3e6` | Body monospace text. |
| `cyber.titleShadow` | `3px 3px 0 #ff00a8, -2px -1px 0 #00e5ff` | Artist-name text shadow string. |
| `cyber.scanlines` | `repeating-linear-gradient(rgba(0,0,0,.16) 0 1px, transparent 1px 3px)` + `mix-blend-mode: multiply; opacity: .5` | Full-screen scanline overlay (line 239). |
| `cyber.spotifyGreen` | `#1db954` | "Open in Spotify" CTA. |

### 1.9 Status / overlay tokens

| Token | Value | Use |
|---|---|---|
| `overlay.dim` | `rgba(0,0,0,.4)` | Day-menu backdrop. |
| `overlay.deep` | `rgba(0,0,0,.5)` | Filter-sheet backdrop. |
| `overlay.notch` | `rgba(0,0,0,.4)` (with `1px solid #00e5ff`) | Artist-screen back-button. |
| `overlay.scrim` | `linear-gradient(to top, rgba(8,6,15,.55), transparent 70%)` | Group-card hero scrim. |

## 2. Typography tokens

### 2.1 Font families

Loaded from Google Fonts in the prototype (`@import` of `Orbitron`, `Playfair Display`, `Manrope`, `Space Mono`, `VT323`). For the Expo app, **load via `expo-font`** at app start. Each file is bundled with the build — no runtime Google Fonts request.

| Token | Family | Weights | Asset |
|---|---|---|---|
| `font.display` | Orbitron | 500, 700, 900 | `assets/fonts/Orbitron-{Medium,Bold,Black}.ttf` |
| `font.serif` | Playfair Display | 600, 700, 800 + italic 600 | `assets/fonts/PlayfairDisplay-{SemiBold,Bold,ExtraBold,SemiBoldItalic}.ttf` |
| `font.sans` | Manrope | 400, 500, 600, 700, 800 | `assets/fonts/Manrope-{Regular,Medium,SemiBold,Bold,ExtraBold}.ttf` |
| `font.mono` | Space Mono | 400, 700 | `assets/fonts/SpaceMono-{Regular,Bold}.ttf` |
| `font.retro` | VT323 | 400 | `assets/fonts/VT323-Regular.ttf` |

`expo-font` family names must exactly match the asset filename minus the extension; the implementer wires this in FE-101.

### 2.2 Type scale (verbatim from prototype `style="font:..."` rules)

| Token | CSS | Example use |
|---|---|---|
| `text.title.xl` | `font: 900 30px Orbitron; letter-spacing: 0.03em` | "GROUPS" home title. |
| `text.title.lg` | `font: 900 28px Orbitron; letter-spacing: 0.02em` | Group-detail title. |
| `text.title.md` | `font: 800 26px Manrope; letter-spacing: -0.01em` | "Join a group" heading. |
| `text.title.sm` | `font: 700 19px Manrope` | "New group" / "Choose event" top-bar. |
| `text.section.serifLg` | `font: 700 30px 'Playfair Display'` | "UP NEXT" artist name. |
| `text.section.serifMd` | `font: 700 22px 'Playfair Display'` | Empty-state heads. |
| `text.section.serifSm` | `font: 700 18px 'Playfair Display'` | Per-set "Mine" / "Group" timeline cards. |
| `text.section.label` | `font: 700 12px Manrope; letter-spacing: 0.08em; text-transform: uppercase` | "Group name" / "Event" form labels. |
| `text.section.head` | `font: 800 20px Manrope` | "Artists" group-detail head. |
| `text.body.lg` | `font: 700 16px Manrope` | Per-set artist names. |
| `text.body.md` | `font: 600 15px Manrope` | Event-list item names. |
| `text.body.sm` | `font: 600 13px Manrope` | Tab labels, "Invite friends" button. |
| `text.meta.lg` | `font: 500 14px Manrope` | Modal subhead. |
| `text.meta.md` | `font: 500 13px Manrope` | Card meta rows. |
| `text.meta.sm` | `font: 500 12px Manrope` | Date / location lines. |
| `text.meta.xs` | `font: 500 11px Manrope` | Filter caption. |
| `text.mono.lg` | `font: 700 18px 'Space Mono'; letter-spacing: 0.18em` | Invite-code input. |
| `text.mono.md` | `font: 700 12px 'Space Mono'; letter-spacing: 0.12em` | Invite code display. |
| `text.mono.sm` | `font: 500 12px 'Space Mono'` | Per-set time labels. |
| `text.mono.xs` | `font: 500 10px 'Space Mono'` | Genre pill text. |
| `text.statusBar` | `font: 700 14px Orbitron` | "9:59" status time. |
| `text.cta` | `font: 700 14px Orbitron; letter-spacing: 0.05em` | "+ CREATE A GROUP" button. |
| `text.tab.orbitron` | `font: 700 12px Orbitron; letter-spacing: 0.08em` | Day-stage heading "SHERWOOD COURT". |
| `text.retro.head` | `font: 400 20px VT323` | Artist-screen section heads. |
| `text.retro.title` | `font: 400 56px VT323; line-height: 0.78` | Artist name on hero. |

### 2.3 Letter-spacing reference

- `letter-spacing: 0.18em` — invite-code input (most aggressive).
- `letter-spacing: 0.12em` — invite-code display chip.
- `letter-spacing: 0.10em` — "UP NEXT" label.
- `letter-spacing: 0.08em` — section labels, day-stage heads.
- `letter-spacing: 0.05em` — CTA "+ CREATE A GROUP".
- `letter-spacing: 0.03em` — main title "GROUPS".
- `letter-spacing: 0.02em` — group-detail title.
- `letter-spacing: -0.01em` — large title "Join a group" (slight tightening).

## 3. Spacing, radius, sizing

### 3.1 Padding / gap scale (extracted from inline styles)

| Token | Px | Use |
|---|---|---|
| `space.1` | 4 | Tiny gap inside chips (genre pills internal). |
| `space.2` | 6–7 | Pill-internal gap, day-axis label offset. |
| `space.3` | 8–9 | Inter-card vertical gap; horizontal pill gap. |
| `space.4` | 10–11 | Form-field gap; row gap inside group card. |
| `space.5` | 12–13 | Card padding (smaller cards). |
| `space.6` | 14–15 | Card padding (larger cards), section title-to-subtitle. |
| `space.7` | 16 | Sheet top padding, card-row gap. |
| `space.8` | 18 | Section header → body. |
| `space.9` | 22 | Screen horizontal margin (`padding: 0 22px`). |
| `space.10` | 26 | Join screen left/right padding. |
| `space.11` | 30 | Modal padding (filter sheet) bottom. |
| `space.12` | 34 | CTA distance to bottom edge. |
| `space.13` | 46 | Heading top spacer on join screen. |

Mobile screen padding default = `space.9` (22 px) — every screen uses it on the body content; tighter values are local exceptions.

### 3.2 Border-radius scale

| Token | Px | Use |
|---|---|---|
| `radius.xs` | 2 | Cyber-retro flat tiles (genre pill, similar-artist tiles). |
| `radius.sm` | 7 | Member-roster check-box. |
| `radius.md` | 11–13 | Most cards (event-list, search input, "Invite friends" button). |
| `radius.lg` | 14 | Larger cards, input fields. |
| `radius.xl` | 15 | CTAs. |
| `radius.2xl` | 18 | "Up Next" timeline card. |
| `radius.3xl` | 20 | Group-card. |
| `radius.4xl` | 22 | Bottom nav. |
| `radius.5xl` | 24–24–0–0 | Filter sheet top corners (`24px 24px 0 0`). |
| `radius.full` | 99 / 50% | Pills + circular avatars. |
| `radius.device` | 46 | Outer device frame. |

### 3.3 Component sizing

| Token | Value | Use |
|---|---|---|
| `size.deviceFrame` | `390 × 844 px` (iPhone 14 native) | Prototype device. RN apps target real device width — token is reference only. |
| `size.avatar.lg` | 40 × 40 | Top-right user avatar. |
| `size.avatar.md` | 34 × 34 | Filter-sheet member roster. |
| `size.avatar.sm` | 26 × 26 | "Going" timeline avatar, picked-check circle. |
| `size.avatar.xs` | 24 × 24 | Stacked-avatar `stk`. |
| `size.avatar.xxs` | 18 × 18 | "Going" inline icon. |
| `size.cta` | 52–54 × full | Primary CTA height. |
| `size.input` | 54 × full | Form input. |
| `size.search` | 48 × full | Search field. |
| `size.button.sm` | 38 × 38 | Back / close round buttons. |
| `size.statusBarOffset` | 44 px | Top reserved area for OS status bar. |
| `size.bottomNav` | 64 × `(screen - 28)` | Glass nav floating from bottom (16 px bottom inset + 14 px sides). |
| `size.eventTile` | 46 × 46 | Event-picker tile (the `mono`-letter square). |
| `size.gridColumn` | 148 px wide | Schedule grid stage column. |
| `size.gridColumnGap` | 10 px | Between stage columns. |
| `size.gridHourPx` | 84 px | Vertical pixels per hour in the grid (`PXH=84`, line 661). |
| `size.gridLeftAxis` | 48 px | Left-axis gutter for hour labels. |

### 3.4 Avatar stacking

The `.stk` class (lines 17–18) overlaps avatars by **-7 px** with a **2 px ring** in `--ring` color (defaulting to `#140e34`). The cyber-retro ring is `#1a0820`; the timeline ring is `#1c143a`.

## 4. Effects — shadows, blurs, animations

### 4.1 Shadows

| Token | Value | Use |
|---|---|---|
| `shadow.device` | `0 24px 70px rgba(20,8,48,.6)` | Device frame drop. |
| `shadow.ctaActive` | `0 10px 26px rgba(166,75,255,.45)` | Active gradient CTA. |
| `shadow.scheduleBtn` | `0 8px 20px rgba(166,75,255,.4)` | Group-detail "Schedule" button. |
| `shadow.cardInsetTop` | `inset 0 1px 0 rgba(255,255,255,.06)` | Group-card top-edge highlight. |
| `shadow.dayMenu` | `0 16px 40px rgba(0,0,0,.5)` | Day menu lift. |
| `shadow.stageDotGlow` | `0 0 8px {{ stage.color }}` | Per-stage timeline dot glow (line 378). |

### 4.2 Blurs

- `backdrop-filter: blur(18px)` — bottom nav (line 463). Implement on RN with `expo-blur` `BlurView intensity={50} tint="dark"`; visual equivalence noted in FE-100 § 7.

### 4.3 Animations (raw `@keyframes` from line 22–25)

```
@keyframes pop      { 0%  { transform: scale(.85) }
                      60% { transform: scale(1.06) }
                      100%{ transform: scale(1) } }
@keyframes sheetUp  { from { transform: translateY(100%) }
                      to   { transform: translateY(0) } }
@keyframes fadeIn   { from { opacity: 0 }
                      to   { opacity: 1 } }
```

| Token | Duration / easing | RN implementation |
|---|---|---|
| `motion.pickCheckPop` | 250 ms (pop keyframes — bounce overshoot at 60%) | `react-native-reanimated` `withSequence(withTiming(.85, 0), withTiming(1.06, 150), withTiming(1, 100))`. |
| `motion.sheetUp` | 250 ms ease-out | `react-native-reanimated` `withTiming({ translateY: 0 }, 250)` from `translateY: 800`. |
| `motion.fadeInScreen` | 250 ms (`fadeIn .25s`) | Used on every screen transition; apply via React Navigation's screen `cardStyleInterpolator` or `react-native-reanimated` fade. |
| `motion.fadeInFast` | 200 ms (`fadeIn .2s`) | Event-picker, artist screen — slightly faster. |
| `motion.fadeInToast` | 200 ms (`fadeIn .15s`) | Day-menu, filter-sheet backdrop. |
| `motion.toastInvite` | 2600 ms hold before fade-out (`setTimeout 2600`, line 605) | "Invite copied" duration. |
| `motion.tapState` | 180 ms (`transition: .18s`, line 207, 327) | Pick-cycle button state change. |
| `motion.cardState` | 200 ms (`transition: .2s`, line 91) | Create-button enabled/disabled cross-fade. |

## 5. Cyber-retro aesthetic divergence (OQ-02 — intentional)

The artist-detail screen uses a different visual language than the rest of the app, on purpose. This section documents the divergence so it isn't read as inconsistency in code review.

- Fonts: `VT323` (display) + `Space Mono` (body) instead of `Manrope` + `Orbitron`.
- Colors: acid yellow `#f5ff00` + hot pink `#ff00a8` + cyan `#00e5ff` on near-black `#0d0818`. No purples or lilacs.
- Shapes: 2-px radius (flat tiles) instead of 11–20 px.
- Texture: a scanline overlay layer (`repeating-linear-gradient` + `mix-blend-mode: multiply`) covers the whole screen.
- Title styling: dual-offset text-shadow (3px pink, 2px cyan) recreates a chromatic-aberration print effect.
- A Spotify-green button (`#1db954`) sits at the bottom — the one color in the app that's not negotiable because it's Spotify's brand.

This is consistent with prototype intent (FE-007 maps directly to `isArtist` screen). Implementer in FE-007 should not "fix" the divergence.

## 6. Implementation notes

1. **NativeWind colors.** Translate § 1.x to a `tailwind.config.ts` `theme.extend.colors` map. NativeWind v4 supports nested keys (`bg.canvas` → `bg-canvas`). RGBA strings need named tokens, not `--var()` interpolation.
2. **Gradient strings.** RN doesn't have native CSS gradient parsing. Use `react-native-linear-gradient` with explicit `colors`, `start`, `end` props; encode the prototype's `120deg` / `135deg` as `start: { x: 0, y: 0.5 }, end: { x: 1, y: 0.5 }` (120°) and `start: { x: 0, y: 0 }, end: { x: 1, y: 1 }` (135°). Document mappings in `apps/mobile/src/theme/gradients.ts`.
3. **Backdrop blur.** `backdrop-filter` is web-only; use `expo-blur` `<BlurView intensity={50} tint="dark">` for `bg.glassNav`.
4. **Text gradient.** RN has no `background-clip: text`; use `react-native-text-gradient` or a `MaskedView` from `@react-native-masked-view/masked-view`. FE-101 picks one and standardizes a `<GradientText>` primitive.
5. **Stage dot glow.** Box-shadow with blur on RN requires `shadowColor / shadowOpacity / shadowRadius` on iOS and `elevation` on Android — neither handles colored glow well. FE-101 should ship a `<StageDot>` primitive that renders a translucent halo `View` sized 1.6× behind a solid `View` for visual parity.
6. **Status bar.** The prototype's "9:59 / 5G ▮▮ 70" custom strip is mocked. Real app uses Expo's `StatusBar` set to `light-content`; the absolute-positioned strip from the prototype is discarded.
7. **Font weights.** Manrope is loaded with five weights (400/500/600/700/800). Expo's `useFonts` registers each as a distinct family name in JS (e.g. `Manrope_500Medium`); the implementer in FE-101 picks one of two patterns (variant family names vs custom font-family + numeric weight on a single font asset) and standardizes.

## 7. References

- Prototype source: [`docs/design/FestApp.dc.html`](../../../docs/design/FestApp.dc.html)
- EPIC: [EPIC.md](./EPIC.md)
- Open question OQ-02 (mixed aesthetic): [EPIC § 7](./EPIC.md#7-open-questions-for-jerome)
- Open question OQ-04 (light theme): [EPIC § 7](./EPIC.md#7-open-questions-for-jerome)
