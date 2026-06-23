# FE-007 — Artist detail (cyber-retro accent) (prototype `isArtist`)

**Wave:** 3
**Type:** FE
**Blocked by:** FE-101, BE-019
**Blocks:** —
**ADR references:** Prototype `isArtist` block (lines 237–280); [artist-drilldown-spec](../../features/artist-drilldown-spec.md); EPIC OQ-02

## 1. Problem statement

Tap any artist (from FE-005 or FE-006). Open a full-screen detail view in the cyber-retro aesthetic (OQ-02): hero with the artist name in VT323 with chromatic-aberration text shadow, scanline overlay, genre pills, friends-going indicator, top tracks (Spotify), similar artists (Spotify/Last.fm/heuristic), Spotify CTA.

## 2. Actual solution

`ArtistDetail` screen pushed onto the current stack (Home or Schedule). `route.params.artist_name`.

Fetches `GET /api/artists/{artist_name}` via TanStack (cache 1 hour client-side; server cache is 7 days).

Layout:

- Full-bleed `bg.cyber.bg` (`#0d0818`).
- Scanline overlay layer (`repeating-linear-gradient` faked with SVG `<Pattern>` or a static asset).
- Hero (280 px) with `A.heroBg` (a deterministic radial picked by hash of artist name).
- Hero scrim `gradient.heroFadeIn`.
- Back chip (cyber styled — `cyber.acid` border).
- Artist name (VT323 56 px line-height 0.78) with `cyber.titleShadow` chromatic-aberration shadow (use `react-native-svg` `<Text>` with stroke OR three stacked Text views).
- Genre pills (Space Mono 700 10 px, rotating through 3 color schemes).
- "Friends going" pill: hot-pink border + AvatarStack + label "X, Y GOING" or "NO ONE GOING YET".
- "▸ TOP TRACKS" section (VT323 20 px, `cyber.acid`):
  - 3 tracks (or what BE returned). Each: 36×36 play button (gradient or outline) + name + "3:48 // 30s" meta. Tap to start preview audio.
- "▸ SIMILAR" section: horizontal scroll of 64×64 tiles + name.
- Bottom: full-width Spotify-green CTA "Open in Spotify" → `Linking.openURL(spotify_url)`.

Audio playback: `expo-av` `Audio.Sound` instance — load `preview_url`, play, pause; only one playing at a time. Stops on screen unmount.

Tap a similar artist → push another `ArtistDetail` onto the stack (recursive navigation works fine).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `apps/mobile/package.json` | Add `expo-av`, `react-native-svg`. |
| `apps/mobile/src/screens/artist/ArtistDetail.tsx` | Screen. |
| `apps/mobile/src/screens/artist/ArtistHero.tsx` | Hero w/ VT323 + shadow. |
| `apps/mobile/src/screens/artist/GenrePills.tsx` | Genre chip row. |
| `apps/mobile/src/screens/artist/TopTracks.tsx` | Track list with audio. |
| `apps/mobile/src/screens/artist/SimilarArtists.tsx` | Horizontal scroll. |
| `apps/mobile/src/screens/artist/ScanlineOverlay.tsx` | Repeating-linear-gradient stand-in. |
| `apps/mobile/src/screens/artist/FriendsGoingPill.tsx` | Hot-pink-border pill. |
| `apps/mobile/src/hooks/useArtistDetail.ts` | TanStack query. |
| `apps/mobile/src/hooks/useAudioPreview.ts` | expo-av wrapper. |
| `apps/mobile/src/theme/cyber.ts` | Centralized cyber-retro tokens (from DESIGN-TOKENS § 1.8). |
| `apps/mobile/src/utils/artistHero.ts` | Deterministic hero gradient + similar-tile gradient from artist name hash. |
| `apps/mobile/__tests__/screens/ArtistDetail.test.tsx` | See § 7. |
| `apps/mobile/__tests__/hooks/useAudioPreview.test.ts` | See § 7. |
| `apps/mobile/__tests__/utils/artistHero.test.ts` | See § 7. |

## 4. Method signatures / new APIs

```typescript
// useArtistDetail.ts
export function useArtistDetail(artistName: string): UseQueryResult<ArtistDetailResponse>;

// useAudioPreview.ts
export function useAudioPreview(): {
  play: (url: string, key: string) => Promise<void>;
  pause: () => Promise<void>;
  playingKey: string | null;
};

// artistHero.ts
export function deriveHero(name: string): string;          // radial-gradient stops
export function deriveSimilarTile(name: string): string;   // 135deg gradient
```

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Hero height | 280 px | Prototype line 241. |
| Title font | VT323 400 56px line-height 0.78 | Prototype line 245. |
| Title chromatic shadow | `3px 3px 0 #ff00a8, -2px -1px 0 #00e5ff` | Prototype line 245. |
| Section head font | VT323 400 20px, color `cyber.acid` | Prototype line 258. |
| Top-track button (active) | `linear-gradient(135deg, #ff00a8, #f5ff00)` | Prototype line 638. |
| Top-track button (idle) | bg `rgba(20,8,38,.6)` + 1 px `#4a3868` border | Prototype line 638. |
| Spotify CTA | `#1db954` solid, white text | DESIGN-TOKENS § 1.8. |
| Preview clip duration | 30 s (capped by Spotify) | Spotify quirk. |
| Audio category | `playback` (iOS) / unrestricted (Android) | Allows playback with mute switch on. |
| Similar tile size | 64 × 64 | Prototype line 273. |
| Scanline opacity | 0.5 with `mix-blend-mode: multiply` simulated | DESIGN-TOKENS § 1.8. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| `top_track == null` | Hide the Spotify CTA OR show it disabled? Show it — it can still link to artist page if `spotify_artist_id` present; otherwise hide entirely. |
| Cache miss + all providers failed → BE 503 | Show "Artist details unavailable" + retry. The hero name still renders from `route.params.artist_name`. |
| `cache_status="stale"` | Render the cached data; show a tiny "data may be stale" hint? **No** — UX-noisy. Just render. |
| Preview URL missing (Spotify removed it) | Play button greyed; disable interaction. |
| User taps a similar artist | Push new ArtistDetail onto stack; previous instance pauses its audio. |
| User navigates away mid-playback | Audio stops on unmount. |
| User backgrounds the app mid-playback | iOS continues if `playback` category; Android pauses. Acceptable. |
| Artist name URL-encoded with special chars (`H&rry`) | useArtistDetail URL-encodes via `encodeURIComponent`. |
| `similar_artists` is empty | Hide the SIMILAR section. |
| `genres` is empty | Hide the genre pills row. |
| `friends going` count == 0 | "NO ONE GOING YET" label; AvatarStack hidden. |
| `friends going` includes the current user | Label says "YOU, NAME GOING" — capitalize own name as "YOU". |
| Long artist name (> 12 chars) | VT323 scales down OR wraps. Choose: 2-line cap with line-height tight. |
| Long track name | Single-line truncation. |
| Multiple recursive ArtistDetail screens stacked | Each maintains independent audio; only one plays. |

## 7. Acceptable validation

**Tests:**

| File | Test name | Assertion |
|---|---|---|
| `artistHero.test.ts` | `hero_deterministic_by_name` | Same name → same gradient string. |
| `artistHero.test.ts` | `different_names_yield_different_heroes` | "A" vs "B" → different strings. |
| `useAudioPreview.test.ts` | `play_loads_and_plays_sound` | Mock expo-av → `Audio.Sound.createAsync` called with url; `playAsync` called. |
| `useAudioPreview.test.ts` | `pause_pauses_current` | playingKey="A"; pause → `pauseAsync` called. |
| `useAudioPreview.test.ts` | `play_new_key_pauses_old` | play("A"); play("B") → A's sound unloaded; B playing. |
| `ArtistDetail.test.tsx` | `renders_artist_name_uppercase` | "eggy" → "EGGY" visible. |
| `ArtistDetail.test.tsx` | `renders_genres_when_present` | 3 genres → 3 pills. |
| `ArtistDetail.test.tsx` | `hides_genres_when_empty` | empty → row absent. |
| `ArtistDetail.test.tsx` | `friends_going_label_caps_you` | friends includes self → label has "YOU". |
| `ArtistDetail.test.tsx` | `no_friends_shows_default_label` | empty → "NO ONE GOING YET". |
| `ArtistDetail.test.tsx` | `tap_top_track_invokes_play` | Tap → useAudioPreview.play called. |
| `ArtistDetail.test.tsx` | `tap_similar_pushes_new_artist_detail` | Tap → navigation.push("ArtistDetail", { artist_name }). |
| `ArtistDetail.test.tsx` | `tap_spotify_cta_calls_linking` | Tap → `Linking.openURL` with `top_track.spotify_url` OR artist URL. |
| `ArtistDetail.test.tsx` | `503_shows_unavailable_state` | Mock 503 → "Artist details unavailable" visible. |
| `ArtistDetail.test.tsx` | `back_chip_pops_screen` | Tap back → goBack. |
| `ArtistDetail.test.tsx` | `unmount_stops_audio` | Render → play → unmount → expo-av `unloadAsync` called. |

**Manual QA — DARK MODE ONLY (the cyber-retro aesthetic is intentional — OQ-02):**

1. From FE-005 or FE-006 tap an artist → screen opens.
2. Title in yellow VT323 with pink + cyan offset shadow. Scanlines visible.
3. Tap a track → 30s preview plays; button shows pause icon.
4. Tap "Open in Spotify" → Spotify app or web fallback.
5. Tap a similar artist → new screen pushes.
6. Back chip → pops.
7. Visual parity with prototype lines 237–280.

**Structured-log lines:** N/A.

## 8. Out of scope

| Item | Where |
|---|---|
| Full-track playback (requires Spotify SDK + premium) | v2 — artist-drilldown-spec. |
| Add-to-Spotify-playlist | v2. |
| Setlist.fm setlist | Permanently out. |
| Lyrics | Out. |
| User-submitted artist info | Out. |
| Light theme | BACKLOG-001 — note this screen is cyber-retro regardless of light/dark per OQ-02. |

## 9. Structured-log events

N/A.

## 10. Rollback plan

Revert. Artist taps in FE-005/FE-006 are no-ops or show placeholder.
