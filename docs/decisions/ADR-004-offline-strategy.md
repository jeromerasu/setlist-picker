# ADR-004: Offline strategy

## Status
**Accepted (revised 2026-06-18).** Supersedes the original "PWA + IndexedDB + Workbox service worker" direction. Native client store is `expo-sqlite` for the write queue + cached lineup, plus `AsyncStorage` for tiny key/value. **The LWW reconciliation algorithm is unchanged.**

## Context
The user is at a live event with unreliable Wi-Fi. They open the app to pick a set, the network drops, the app freezes — that's the v1 failure mode we cannot ship.

[ADR-001](ADR-001-tech-stack.md) was revised on 2026-06-18 to lock in React Native + Expo as the v1 client (iPhone + Android, no PWA). This ADR is the corresponding offline-strategy update — the original IndexedDB + Workbox design was built around the retired PWA stack.

## Decision

On-device SQLite (via `expo-sqlite`) for the offline write queue + cached lineup snapshot + cached group state. `AsyncStorage` for tiny key/value (auth tokens, user prefs, last-known-server-time). Same last-write-wins reconciliation algorithm as before.

- **Cached read data** lives in `expo-sqlite`:
  - The lineup payload for the user's group's event (stages + sets + artists). Refreshed on app foreground if connectivity is healthy and the cached copy is > 1h old.
  - The most recent `GET /api/groups/{invite_code}` snapshot (members + picks). Refreshed by the 15s foreground poll ([ADR-006 § 4.14](ADR-006-initial-data-schema.md)); cached aggressively for the offline-first read path.
- **Write queue** in `expo-sqlite`:
  - Table `pending_pick_op(id TEXT PK, action TEXT, set_id TEXT, state_clock_ms INTEGER, queued_at INTEGER)`.
  - `action` ∈ `{add_pick, remove_pick}`.
  - Every pick toggle while offline (or while the network request is in flight) is inserted into this table.
  - On reconnect: drain oldest-first via `POST /api/groups/{invite_code}/picks/sync` (bulk drain endpoint per [v1_pydantic.py](../schemas/reference/v1_pydantic.py)). On 2xx, delete the drained rows.
- **AsyncStorage** holds:
  - JWT access + refresh tokens (mirror via `expo-secure-store` on iOS Keychain / Android Keystore for at-rest protection on the secret values).
  - User prefs (last selected day tab, last selected stage filter).
  - Last successful poll timestamp (drives the "Offline — changes will sync" badge heuristic).
- **Reconciliation** is last-write-wins (unchanged):
  - The server's `pick.state_clock_ms` LWW key is authoritative per [ADR-006 § 4.5](ADR-006-initial-data-schema.md).
  - If the user added then removed the same pick offline, the queue still processes both in order; the server ends up tombstoned (idempotent).
  - The same `member_id` IS used across multiple of the user's devices (one User → one Member per group → same `member_id`). The client clock orders the writes; the LWW algorithm handles it correctly.
- **UI indicators**:
  - "Offline — changes will sync" badge when `NetInfo.isConnected === false` OR the last successful poll is > 60 s ago.
  - "Stale data" warning if the group-state cache is > 4 hours old (probably opened the app on a dead day; refresh strongly recommended).

## Rationale

1. **`expo-sqlite` is the right native primitive.** Single-file SQL store, native to both iOS and Android, no separate schema-versioning ceremony like IndexedDB. Mirrors the server's SQL mental model so the queue + cache logic reads naturally.
2. **Queue model over CRDT.** The v1 mutation surface is small (add pick, remove pick) and idempotent. Last-write-wins is correct enough. CRDT (Yjs / Automerge) is overkill for two-state-per-row data.
3. **AsyncStorage for tokens + small prefs.** The right shape for small flat values where SQL would be overkill. JWTs go via `expo-secure-store` to land in iOS Keychain / Android Keystore — `AsyncStorage` for everything else.
4. **Algorithm-stable, storage-portable.** The reconciliation contract (`state_clock_ms` LWW + tombstone) is the load-bearing part. If the underlying storage layer changes again (e.g. ejecting from Expo to bare RN), only the queue serializer changes, not the contract.

## Consequences

### Positive
- Works underground, on the floor of a sweaty venue, in a tent — anywhere Wi-Fi flakes.
- Predictable conflict resolution (LWW timestamps from the server).
- Native SQL store is faster than IndexedDB and avoids Safari-specific eviction quirks.
- One mobile codebase covers iOS + Android via Expo modules.

### Negative
- LWW can lose well-timed data in edge cases (the same User's two devices toggling the same set within the same second, then reconnecting at different times). Mitigation: client clock plus server-side tie-break by receive order — documented as a known limit; [ADR-006 § 5.3](ADR-006-initial-data-schema.md) covers the clock-skew rejection policy.
- `expo-sqlite` corruption requires an explicit nuke-and-resync; we wrap the queue in a try/catch and on irrecoverable error clear the local DB + re-pull state from the server.
- Stale-warning's 4-hour threshold is heuristic. May need tuning after real-event data.

## Implementation notes

- `expo-sqlite` schema versioning: migration helper on app launch checks a `meta(schema_version)` row and applies forward migrations idempotently.
- The drain runs on app foreground + on `NetInfo` `connected → true` transition; one in-flight drain at a time (mutex flag in memory).
- `expo-secure-store` wraps the JWT tokens; AsyncStorage holds the rest. Tokens are written through a single `auth-store` module — never touched by feature code directly.

## Previous direction (IndexedDB + Workbox, retired 2026-06-18)

**The original ADR-004 specified a Workbox-flavored service worker caching JS/CSS/fonts + lineup JSON + group state, with an IndexedDB write queue for offline pick mutations.** This direction is retired alongside the PWA stack in [ADR-001](ADR-001-tech-stack.md).

Why retired:

- **Service workers don't run on native.** RN + Expo apps don't have the browser's service-worker primitive at all. The caching layer is the native fetch client + `expo-sqlite`.
- **IndexedDB is the wrong tool on a native app.** Expo's `expo-sqlite` is a better fit — SQL-shaped, no Safari eviction quirks, no private-browsing oddities.
- **Workbox versioning + the SW registration lifecycle are dead weight.** A native app's bundle is delivered through the App Store / Play Store / Expo OTA; there's no "refresh on next navigation" caching dance to manage.

If the native ship is reversed for any reason, this section is the recovery context — the original Workbox / IndexedDB design worked, and the LWW algorithm is unchanged either way.

## References
- [PRD.md](../PRD.md) § 5.6
- [ARCHITECTURE.md](../ARCHITECTURE.md) § Offline strategy
- [ADR-001 — Tech stack](ADR-001-tech-stack.md) — locks in RN + Expo + Postgres.
- [ADR-006 — Initial data schema](ADR-006-initial-data-schema.md) § 4.5 LWW + § 4.14 polling.
