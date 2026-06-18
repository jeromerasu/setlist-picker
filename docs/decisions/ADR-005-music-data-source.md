# ADR-005: Music data source

## Status
Accepted

## Context
The artist drill-down feature needs three pieces of data per artist:

1. Genre tags.
2. A small set of similar / related artists.
3. A top track (name + 30-second preview clip + link to a streaming service).

We need a source that has good coverage of festival-circuit artists across genres (electronic, hip-hop, pop, indie). The source also needs to be queryable from a small Python backend without per-user OAuth flow — we don't want the user signing in to anything just to see what genre a DJ plays.

## Decision

**Primary source: Spotify Web API.** Backend-only access via Spotify's Client Credentials grant.

- The backend stores `SPOTIFY_CLIENT_ID` + `SPOTIFY_CLIENT_SECRET` in environment variables (Render env vars at deploy time; `.env` for local dev).
- The backend exchanges them for a bearer token every hour and caches it in memory.
- The frontend never sees the token or the credentials.

Endpoints used:

| Endpoint | Purpose |
|---|---|
| `GET /v1/search?type=artist&q=<name>` | Look up Spotify artist ID by name. |
| `GET /v1/artists/{id}` | Genre tags, images. |
| `GET /v1/artists/{id}/top-tracks?market=US` | Top track with 30-second preview URL. |

**Similar artists — fallback chain.** Spotify deprecated the `related-artists` endpoint in late 2024. Fallback chain:

1. **Last.fm** `artist.getsimilar` (free; requires an API key). Returns a list of similar artists with similarity scores.
2. **Genre-overlap heuristic** from our own `artist_cache`. If Last.fm fails too, surface 5 cached artists with the highest Jaccard similarity on `genres` arrays.
3. If neither is available, the modal renders "Similar artists unavailable" gracefully.

Each cache row records which source the similar-artists list came from in a `similarity_source` field (`spotify_v2_endpoint` / `lastfm` / `genre_overlap` / `none`) so we can swap or improve the chain later.

**Caching policy.**

- `artist_cache` rows keyed on `lower(artist_name)`.
- TTL: 7 days. Artists rarely change.
- Backoff on failure: `fetch_failure_count` doubles the next retry interval, capped at 24 hours. Cleared on successful refresh.
- Pre-warm strategy: when a new lineup is imported, the backend kicks off a background job that walks every distinct artist name and populates the cache. Avoids the herd of cold-cache misses at event start.

## Rationale

1. **Spotify has the best breadth** for festival-circuit artists. Worse coverage on small / underground / region-specific acts, but that's a known gap; the fallback heuristic helps.
2. **Client Credentials grant** keeps the user out of any OAuth flow. The integration is invisible to them.
3. **Caching aggressively** matters because we'll see thundering-herd traffic at event start when everyone opens the app and taps the headliner. 7-day TTL means even a re-deploy doesn't re-hit Spotify for known artists.
4. **Genre-overlap fallback** is cheap and reasonable when both external sources fail. Not perfect but acceptable.

## Consequences

### Positive
- High coverage, free tier sufficient for v1.
- No user-side OAuth.
- Graceful degradation chain.

### Negative
- Spotify API rate limits (currently 100 requests/sec across the app; well within our needs but worth monitoring).
- Spotify could deprecate further endpoints; the abstraction layer in `services/api/app/integrations/music_data.py` (planned name) gives us a single point to swap.
- Last.fm API requires its own key + has its own rate limits.

## Implementation notes

- The integration layer lives at `services/api/app/integrations/music_data.py`. Mockable in tests.
- A `MusicDataProvider` Protocol defines the interface. `SpotifyProvider` + `LastFmProvider` + `GenreOverlapProvider` implement it. The cache layer composes them.
- Spotify credentials in `services/api/.env.example` as `SPOTIFY_CLIENT_ID` / `SPOTIFY_CLIENT_SECRET` (placeholders).
- Background pre-warm job runs on event import; tracked via a `cache_prewarm` audit row.

## References
- [features/artist-drilldown-spec.md](../features/artist-drilldown-spec.md)
- [ARCHITECTURE.md](../ARCHITECTURE.md) § External integrations
