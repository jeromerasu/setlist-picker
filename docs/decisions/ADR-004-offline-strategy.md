# ADR-004: Offline strategy

## Status
Accepted

## Context
The user is at a live event with unreliable Wi-Fi. They open the app to pick a set, the network drops, the app freezes — that's the v1 failure mode we cannot ship.

## Decision

Progressive Web App with a service worker + IndexedDB write queue.

- **Service worker** (Workbox) caches:
  - All JS / CSS / fonts (cache-first; refresh-on-update).
  - The lineup JSON (cache-first; refresh-when-online).
  - The currently-viewed group state (stale-while-revalidate).
- **IndexedDB write queue** for offline pick mutations:
  - Schema: `{action: 'add_pick' | 'remove_pick', member_id, set_id, queued_at}`.
  - Every pick toggle while offline is appended to the queue.
  - On reconnect: drain oldest-first, post each action to the API.
- **Reconciliation** is last-write-wins:
  - The API's `picked_at` and `removed_at` timestamps are authoritative.
  - If the user added then removed the same pick offline, the queue still processes both in order; the API ends up with no pick (idempotent).
  - If the user added a pick that another member added at the same time, both ledger entries succeed — picks are per-member.
- **UI indicators**:
  - "Offline — changes will sync" badge when `navigator.onLine === false` OR the last successful poll is > 60 s ago.
  - "Stale data" warning if the group-state cache is > 4 hours old (probably opened the app on a dead day; refresh strongly recommended).

## Rationale

1. **Service worker first.** The lineup is mostly static (changes once at import; rarely updates). Cache it aggressively. Group state is dynamic but small.
2. **Queue model over CRDT.** The v1 mutation surface is small (add pick, remove pick) and idempotent. Last-write-wins is correct enough. CRDT (Yjs) is overkill for two-state-per-row data.
3. **Polling friendliness.** Online mode polls every 5 s. The service worker's stale-while-revalidate naturally fits — show cached data instantly, refresh from network.

## Consequences

### Positive
- Works underground, on the floor of a sweaty venue, in a tent — anywhere Wi-Fi flakes.
- Predictable conflict resolution (LWW timestamps from the server).
- Small implementation surface (Workbox does the heavy lifting).

### Negative
- LWW can lose well-timed data in edge cases (two devices with the same `member_id` toggling the same set offline, within the same second, then reconnecting at different times). Mitigation: same `member_id` doesn't happen across devices in v1.
- IndexedDB has Safari-specific quirks (eviction policy, private-browsing behavior). Acceptable for v1; documented as a known limitation.
- Stale-warning's 4-hour threshold is heuristic. May need tuning.

## Implementation notes

- Service worker scope: `/`. Registers on first visit; updates checked on every navigation.
- Workbox version: pin to latest LTS at the time of build.
- IndexedDB schema versioning: explicit version numbers, migration code in the SW registration script.

## References
- [PRD.md](../PRD.md) § 5.6
- [ARCHITECTURE.md](../ARCHITECTURE.md) § Offline strategy
