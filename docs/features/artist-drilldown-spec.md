# Feature Spec — Artist Drill-Down

**Status:** Approved scope; ready for ticket decomposition.
**Last updated:** 2026-06-18

## Problem

When a user sees an artist on the calendar they don't recognize, they need a fast answer to "what kind of music do they make and should I go?" A 1-tap modal with genre + similar artists + a 30-second preview lets them decide.

## Scope (v1)

- Tap any artist name (on a set card, in the member-pick list, anywhere their name appears) → an artist modal opens.
- **Modal contents:**
  - Artist photo (Spotify).
  - Artist name (large heading).
  - Genre tags (chips).
  - **Similar artists** (3–6 items). Each clickable to open that artist's drill-down. Fallback chain: Spotify → Last.fm → genre-overlap heuristic. See [ADR-005](../decisions/ADR-005-music-data-source.md).
  - **Top track** — track name + 30-second audio preview button (Spotify's preview clip). Link to "Open in Spotify" if user has Spotify installed.
- **Backend handles all music-data API calls.** Frontend never holds an API key.
- **7-day cache** in the `artist_cache` table. Backoff on repeated failures.

## Out of scope (v1)

- Full track playback (requires Spotify SDK + premium account; v2).
- Add-to-Spotify-playlist integration.
- Setlist.fm setlist preview.
- Lyrics.
- User-submitted artist info.

## Data flow

```
Frontend tap on "DJ Example"
  → GET /api/artists/DJ%20Example
    Backend:
      1. Lower-case "dj example" → check artist_cache.
      2. Cache hit + fresh (< 7 days) → return cached row.
      3. Cache miss / stale / fetch_failure_count not in backoff → fan out:
         a. Spotify search → artist details → top tracks
         b. Spotify similar-artists deprecated → Last.fm getsimilar
         c. Last.fm failure → genre-overlap heuristic from artist_cache
      4. Upsert artist_cache row.
      5. Return populated DTO.
  → Modal renders fields.
```

## Data model

Adds `artist_cache` table (see [ARCHITECTURE.md § Data model](../ARCHITECTURE.md)). No FK to `set` — artist matching is by lower-cased name, intentionally loose so the cache survives lineup re-imports with slightly different casing.

## API contract

- `GET /api/artists/{artist_name}` — returns:
  ```json
  {
    "artist_name": "DJ Example",
    "spotify_artist_id": "...",
    "image_url": "https://...",
    "genres": ["techno", "minimal"],
    "similar_artists": [
      { "name": "DJ Other", "similarity_source": "lastfm" }
    ],
    "top_track": {
      "name": "Track Name",
      "preview_url": "https://...",
      "spotify_url": "https://...",
      "image_url": "https://..."
    },
    "cache_status": "fresh" | "stale" | "miss",
    "fetched_at": "2026-06-18T12:00:00Z"
  }
  ```

## Tickets

| Ticket | Scope | Effort | Depends on |
|---|---|---|---|
| BE-AD-001 | Alembic migration for `artist_cache` table. | XS | none |
| BE-AD-002 | `MusicDataProvider` Protocol + `SpotifyProvider` implementation (search + artist + top-tracks). | M | BE-AD-001 |
| BE-AD-003 | `LastFmProvider` implementation for similar-artists fallback. | S | BE-AD-002 |
| BE-AD-004 | `GenreOverlapProvider` heuristic — Jaccard similarity over cached `genres`. | S | BE-AD-002 |
| BE-AD-005 | `GET /api/artists/{artist_name}` endpoint with cache-first + fallback chain. | S | BE-AD-002, -003, -004 |
| BE-AD-006 | Pre-warm background job — on lineup import, walk distinct artist names + populate cache. | S | BE-AD-005 |
| BE-AD-007 | Tests: cache hit, cache miss + Spotify success, Spotify failure + Last.fm success, both external failures + heuristic. | M | BE-AD-005 |
| FE-AD-001 | Artist modal component — opens when an artist name is tapped anywhere. | S | calendar FE-CAL-001 |
| FE-AD-002 | Modal content layout — photo + name + genre chips + similar-artists list + top-track preview button. | S | FE-AD-001 |
| FE-AD-003 | Audio preview button — Web Audio play / pause; respects `preview_url` absence gracefully. | S | FE-AD-002 |
| FE-AD-004 | Similar-artist navigation — tapping an item swaps the modal to that artist's drill-down. | S | FE-AD-002 |

Ticket files live in [`features/artist-drilldown-tickets/`](artist-drilldown-tickets/).

## Design integrity

- Theme-aware via Tailwind tokens.
- Genre chips use a single shared chip component (reuse across the app).
- Audio preview state: idle / loading / playing / error.
- "Loading similar artists" state needs an explicit skeleton — these can take a beat (especially when Last.fm is queried).
- Modal accessibility: focus trap, ESC to close, `aria-modal` set correctly.

## Acceptance

- ✅ Tapping an artist anywhere opens the modal.
- ✅ Genres render.
- ✅ Similar artists render with fallback chain transparent to the user.
- ✅ Audio preview plays.
- ✅ Cache TTL respected; backoff on repeated failures.
- ✅ Pre-warm job runs on lineup import.
- ✅ All BE-AD-* and FE-AD-* tickets shipped.
- ✅ Screenshots in both light and dark mode.

## References
- [PRD.md § 5.4](../PRD.md)
- [ARCHITECTURE.md § External integrations](../ARCHITECTURE.md)
- [decisions/ADR-005-music-data-source.md](../decisions/ADR-005-music-data-source.md)
