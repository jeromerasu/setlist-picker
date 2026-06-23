# BE-019 — `GET /api/artists/{artist_name}` (cache-first + Spotify + Last.fm + heuristic)

**Wave:** 2
**Type:** BE
**Blocked by:** BE-002
**Blocks:** FE-007
**ADR references:** [ADR-005](../../decisions/ADR-005-music-data-source.md), [ADR-006 § 2.11](../../decisions/ADR-006-initial-data-schema.md), [features/artist-drilldown-spec.md](../../features/artist-drilldown-spec.md)

## 1. Problem statement

The artist modal (FE-007) needs Spotify's genre tags + top track + similar artists. We hold the API keys server-side, cache aggressively (7 days), and fall back through Last.fm and a genre-overlap heuristic per ADR-005.

## 2. Actual solution

`app/services/artist_service.get_artist_detail(db, raw_name) -> ArtistDetailResponse`.

Algorithm:

1. `normalized = normalize(raw_name)` — same as BE-018 (`name_normalized`).
2. SELECT `artist_cache` by PK = `normalized`. If found AND fresh (`fetched_at >= now() - 7 days`) → return cached row with `cache_status="fresh"`.
3. If found AND stale BUT `fetch_failure_count > 0` AND within backoff window (`last_failure_at + min(2^count, 24) hours > now()`) → return cached row with `cache_status="stale"` (no external call).
4. Else, fan out to providers (BE-019 lands the whole stack in one ticket):
   a. `SpotifyProvider.search_and_fetch(normalized)` — search by name, get artist (genres, image), get top tracks.
   b. `LastFmProvider.get_similar(normalized)` — fallback for similar-artists (Spotify's `related-artists` deprecated).
   c. `GenreOverlapProvider.get_similar(normalized, genres)` — final fallback; Jaccard similarity over cached `genres` JSONB.
5. On full success: UPSERT `artist_cache` with `cache_status="fresh"`, `fetched_at=now()`, `fetch_failure_count=0`.
6. On partial success (e.g. Spotify OK but Last.fm down): UPSERT with what we got; `cache_status="fresh"`; `similarity_source` reflects which fallback served. Failure-count not bumped.
7. On total failure: increment `fetch_failure_count`, set `last_failure_at = now()`, return whatever's cached (or 503 `artist_unavailable` if cache empty).

`SpotifyProvider` uses the client-credentials grant — caches the bearer token in-process for `expires_in` seconds, refreshes on demand.

Pre-warm: when `import_lineup_service` (BE-018) finishes, enqueue a background `artist_cache` populate for each distinct artist name. v1 implementation uses an in-process `asyncio.create_task` instead of a real job queue (acceptable for ~400 artists; sequential with `asyncio.gather(*, return_exceptions=True)` capped at 5 concurrent).

## 3. Files to touch

| Path | Edit purpose |
|---|---|
| `services/api/pyproject.toml` | Add `httpx` (likely already present). |
| `services/api/app/config.py` | Add `spotify_client_id`, `spotify_client_secret`, `lastfm_api_key`, `artist_cache_ttl_seconds: int = 604800`, `artist_max_backoff_hours: int = 24`. |
| `services/api/app/services/artist_service.py` | `get_artist_detail`, `_is_fresh`, `_in_backoff`. |
| `services/api/app/services/artist_providers/__init__.py` | Re-exports. |
| `services/api/app/services/artist_providers/protocol.py` | `MusicDataProvider` Protocol. |
| `services/api/app/services/artist_providers/spotify.py` | `SpotifyProvider` — search, artist, top-tracks. |
| `services/api/app/services/artist_providers/lastfm.py` | `LastFmProvider` — `getsimilar`. |
| `services/api/app/services/artist_providers/genre_overlap.py` | `GenreOverlapProvider` — Jaccard. |
| `services/api/app/services/artist_prewarm.py` | `prewarm_artists_from_event(event_id)` — bulk-populate cache. |
| `services/api/app/schemas/artists.py` | `ArtistDetailResponse`, `SimilarArtist`, `TopTrack`. |
| `services/api/app/routes/artists.py` | `GET /api/artists/{artist_name}`. |
| `services/api/app/main.py` | Include router; call `prewarm_artists_from_event` on lineup import (via BE-018 hook). |
| `services/api/.env.example` | Add Spotify + Last.fm env vars. |
| `services/api/tests/test_artist_fetcher.py` | See § 7. |
| `services/api/tests/test_spotify_provider.py` | See § 7. |
| `services/api/tests/test_lastfm_provider.py` | See § 7. |
| `services/api/tests/test_genre_overlap.py` | See § 7. |
| `docs/CODEBASE_GUIDE.md` | Add the endpoint + provider stack. |

## 4. Method signatures / new APIs

```python
# app/services/artist_providers/protocol.py
class MusicDataProvider(Protocol):
    async def search_and_fetch(self, name_normalized: str) -> ProviderArtist | None: ...

class SimilarArtistsProvider(Protocol):
    async def get_similar(self, name_normalized: str, genres: list[str] | None) -> list[SimilarArtist]: ...
```

```python
# app/schemas/artists.py — verbatim from reference
class ArtistDetailResponse(_Model):
    artist_name: str
    spotify_artist_id: str | None
    image_url: str | None
    genres: list[str]
    similar_artists: list[SimilarArtist]
    top_track: TopTrack | None
    cache_status: CacheStatus
    fetched_at: datetime | None
```

Endpoint:

| Method | Path | Response | Status |
|---|---|---|---|
| `GET` | `/api/artists/{artist_name}` | `ArtistDetailResponse` | 200 / 503 |

Errors:

| HTTP | error_code | When |
|---|---|---|
| 503 | `artist_unavailable` | Cache miss + all providers failed. |

URL-encoded artist names: `artist_name` is the raw display name, percent-encoded by the FE. Server URL-decodes before `normalize`.

## 5. Constants and thresholds

| Constant | Value | Rationale |
|---|---|---|
| Cache TTL | 7 days | Artist data rarely changes; minimizes Spotify quota. ADR-005. |
| Backoff base | 1 hour, doubling | `1 → 2 → 4 → 8 → 16 → 24 (capped)`. ADR-005. |
| Backoff cap | 24 hours | ADR-005. |
| Spotify HTTP timeout | 5 s connect / 10 s read | Spotify P95 ≈ 200ms; longer means trouble. |
| Last.fm HTTP timeout | 5 s / 10 s | Similar. |
| Pre-warm concurrency cap | 5 | Stay under Spotify's per-second limit (~10 RPS sustained). |
| Pre-warm timeout per artist | 30 s | If Spotify hangs, give up and move on. |
| Spotify client-credentials token cache | `expires_in - 60 s` | 60-second safety margin. |

## 6. Edge cases enumerated

| Case | Expected behavior |
|---|---|
| Cache hit, fresh | Single DB read, no external calls. `cache_status="fresh"`. |
| Cache hit, stale, no backoff | Fan out → repopulate. |
| Cache hit, stale, in backoff | Return cached row with `cache_status="stale"`. No external calls. |
| Cache miss, all providers succeed | New row with all fields; `cache_status="fresh"`. |
| Cache miss, Spotify fails | Return `cache_status="miss"`? **No.** If we have nothing for the user, we 503. If we get partial data (just genres from Last.fm), we cache that as fresh, `similarity_source="lastfm"`. Document. |
| Cache miss, all providers fail | 503 `artist_unavailable`. Also UPSERT a row with NULLs + `fetch_failure_count=1` so subsequent calls don't slam the providers. |
| Cache hit with old `spotify_artist_id` from `artist` table | Use the `artist.spotify_artist_id` as a hint to Spotify's `/artists/{id}` (cheaper than search). |
| Artist name with special chars (e.g. `H&rry`, `BASSNØVA`) | URL-decoded + normalized; query Spotify with the original (display) name; cache key uses normalized. |
| Concurrent requests for the same artist (cache stampede) | First call triggers external fetch; second call... v1 acceptably duplicates (idempotent UPSERT). v2: per-key lock. Acceptable per ADR-005. |
| Pre-warm for an artist already cached and fresh | Skip — short-circuit on cache hit. |
| Pre-warm for an artist that fails | Increment failure count; logged; doesn't block other artists in the batch. |
| Spotify returns 429 (rate-limited) | Honor `Retry-After`; bump backoff; cache miss returns 503. |
| Last.fm returns empty similar-artists | Try genre-overlap. |
| Genre-overlap with no genres available | Return empty `similar_artists`; `similarity_source="none"`. |

## 7. Acceptable validation

**Tests that MUST exist:**

| File | Test name | Assertion |
|---|---|---|
| `tests/test_spotify_provider.py` | `test_spotify_search_and_fetch_happy_path` | Mock httpx; SpotifyProvider returns `ProviderArtist(genres=..., spotify_id=..., image_url=..., top_track=...)`. |
| `tests/test_spotify_provider.py` | `test_spotify_client_credentials_cached` | First call hits `/api/token`; second within TTL doesn't. |
| `tests/test_spotify_provider.py` | `test_spotify_token_refresh_on_expiry` | Token expires → next call refreshes. |
| `tests/test_spotify_provider.py` | `test_spotify_429_raises_retry_after` | Mock returns 429 + `Retry-After: 30`; SpotifyProvider raises `RateLimited(retry_after=30)`. |
| `tests/test_lastfm_provider.py` | `test_lastfm_getsimilar_returns_list` | Mock → list of names with `similarity_source="lastfm"`. |
| `tests/test_lastfm_provider.py` | `test_lastfm_5xx_returns_empty` | 503 from Last.fm → returns `[]` (provider doesn't raise; caller chains). |
| `tests/test_genre_overlap.py` | `test_jaccard_over_cached_genres` | Seed 3 artists with genres; query artist with overlapping genres → returns artists ranked by Jaccard. |
| `tests/test_artist_fetcher.py` | `test_cache_hit_fresh_returns_without_external_call` | Pre-seed cache; assert SpotifyProvider mock NOT called. |
| `tests/test_artist_fetcher.py` | `test_cache_hit_stale_outside_backoff_refetches` | Stale row + no recent failure → SpotifyProvider called. |
| `tests/test_artist_fetcher.py` | `test_cache_hit_stale_inside_backoff_returns_stale` | Stale row + failure count=3 + recent last_failure_at → SpotifyProvider NOT called; response `cache_status="stale"`. |
| `tests/test_artist_fetcher.py` | `test_cache_miss_all_providers_fail_returns_503` | Mock all to raise → 503 `artist_unavailable`; UPSERT happened with failure_count=1. |
| `tests/test_artist_fetcher.py` | `test_cache_miss_spotify_ok_lastfm_fail_uses_genre_overlap` | Force Spotify OK, Last.fm raise → response `similarity_source="genre_overlap"`. |
| `tests/test_artist_fetcher.py` | `test_backoff_doubles_up_to_24h_cap` | failure_count=1 → 1h; 2 → 2h; 5 → 24h (cap); 6 → 24h. |
| `tests/test_artist_fetcher.py` | `test_concurrent_requests_eventually_consistent` | Two concurrent calls → both 200; cache populated; failure_count ≤ 1. |
| `tests/test_artist_fetcher.py` | `test_unauthenticated_returns_401` | No JWT → 401. |
| `tests/test_artist_fetcher.py` | `test_special_chars_in_name_round_trip` | `GET /api/artists/H%26rry` → matches the cached row keyed `"h&rry"`. |
| `tests/test_artist_fetcher.py` | `test_prewarm_populates_cache_for_event_artists` | Seed event with 10 artists; call prewarm; cache has 10 rows. |
| `tests/test_artist_fetcher.py` | `test_prewarm_skips_already_fresh` | 5 artists already fresh; prewarm → only 5 external calls. |
| `tests/test_artist_fetcher.py` | `test_prewarm_one_failure_does_not_block_others` | One artist's Spotify call raises; other 9 succeed. |

**Manual QA:**

1. Set valid Spotify creds + key.
2. `curl /api/artists/Eggy` → genres + top track + similar.
3. Re-curl → faster (cache hit).
4. Block Spotify on the firewall → curl still works (Last.fm fallback).

**Structured-log lines:**

| Event | Fields |
|---|---|
| `artist.cache_hit_fresh` | `name_normalized`, `request_id` (DEBUG) |
| `artist.cache_hit_stale` | `name_normalized`, `in_backoff: bool`, `request_id` (DEBUG) |
| `artist.fetch_started` | `name_normalized`, `request_id` |
| `artist.fetch_complete` | `name_normalized`, `spotify_ok`, `lastfm_ok`, `similarity_source`, `duration_ms`, `request_id` |
| `artist.fetch_failed` | `name_normalized`, `failure_count`, `next_backoff_seconds`, `request_id` (WARNING) |
| `artist.unavailable` | `name_normalized`, `request_id` (ERROR — returns 503) |
| `artist.prewarm_complete` | `event_id`, `total`, `succeeded`, `failed`, `duration_ms`, `request_id` |

## 8. Out of scope

| Item | Where |
|---|---|
| Distributed rate-limiter coordination | Single-instance v1; if we scale out, BACKLOG-017. |
| Cache stampede prevention (per-key lock) | v2. |
| User-curated similar artists | Out. |
| Setlist.fm setlist preview | Out per artist-drilldown-spec. |
| Lyrics | Out. |

## 9. Structured-log events

(See § 7.)

## 10. Rollback plan

Revert. FE-007 falls back to a "data unavailable" UI; cached rows remain in DB. No data loss.
