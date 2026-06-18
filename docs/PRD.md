# Product Requirements Document — setlist-picker

| Field | Detail |
|---|---|
| Codename | setlist-picker |
| Status | Draft |
| Version | 0.1 |
| Last Updated | 2026-06-18 |
| Stage | 0 → 1 |

## 1. Problem

Coordinating with a group of friends at a multi-stage live event — knowing where each person is at any given moment, which acts everyone is planning to catch, who's splitting off to a side stage — falls apart on group chats and shared spreadsheets. People miss meetups, miss acts they wanted to see, and lose the social fabric that makes going as a group worthwhile.

setlist-picker turns that coordination into a shared, real-time view. Friends pick the acts they want to see, the group sees who's where, and it all works offline once you're at the venue.

## 2. Goals & Success Metrics

### Goals
- Under 30 seconds from receiving an invite link to picking your first act.
- At-a-glance "who's where right now" for any moment in the event.
- Works offline once loaded. Dead zones, dead Wi-Fi, dead battery saver — the app keeps working.
- Privacy-light: no account, no email, no PII beyond a display name and a group code.

### Success Metrics (post-launch)

| Metric | Target |
|---|---|
| Active groups in a launch event window | ≥ 500 |
| Avg. members per group | ≥ 4 |
| Avg. picks per user | ≥ 8 |
| Offline pick success rate (changes made offline that sync) | ≥ 95% |
| Day-1 return rate during the event | ≥ 60% |

## 3. Target Users

| Persona | Description |
|---|---|
| Group-Goer | Attending with 5–10 friends, wants coordination without signup hassle. |
| Solo Explorer | Going alone or with one friend; uses the app to plan their own day across many stages. |
| The Organizer | The friend who plans + shares the group setup. De facto admin in every friend group. |

## 4. Scope

### In Scope (v1)

- **Group lifecycle.** Anyone creates a group → gets a shareable invite link with an 8-character code. Friends open the link, enter a display name, join. No email, no signup.
- **Calendar UI.** A visual day/week calendar showing every act on every stage, scrollable by time and filterable by stage.
- **Setlist import.** Lineup data loaded from a JSON file matching the schema in [`data/lineup-schema.example.json`](../data/lineup-schema.example.json). Files dropped into `data/` ship with the deploy; admin import endpoint lets the host paste JSON into a deployed instance without redeploying.
- **Pick / unpick.** Tap an act to pick it (it goes on your schedule). Tap again to unpick.
- **Friends list / group view.** See who's in your group with a colored initial avatar each. Every act on the calendar shows which group members are planning to be there.
- **Artist drill-down.** Tap an artist on the calendar → see their genre tags, related/similar artists, and a top track preview. Powered by Spotify's API on the backend with aggressive caching; the frontend never holds an API key.
- **Time conflict warnings.** If you pick two acts that overlap, the UI flags it visibly.
- **Offline mode.** Service worker caches the lineup + group state. Pick mutations queue locally in IndexedDB. Sync on reconnect with last-write-wins.

### Out of Scope (v1)

- User accounts, login, cross-device sync (the group code IS the credential — open it on any device).
- Direct messaging between members. Use whatever group chat you already use.
- Push notifications for friend updates.
- Multi-event groups (one group ↔ one event in v1).
- Native mobile apps. The PWA is the mobile experience.
- HIPAA / GDPR specific compliance work beyond the basics (no PII collected reduces surface area significantly).

## 5. Features & Requirements

### 5.1 Group Lifecycle

- 8-character base32 (Crockford alphabet) group code, ~1.1 trillion unique codes.
- Group has a name (defaults to "Friends 🎵"); the creator can rename.
- Group persists for 90 days after last activity, then archives (data retained but read-only).
- The URL is the credential. Anyone with the URL can join the group as any display name.

### 5.2 Calendar UI

See [`features/calendar-spec.md`](features/calendar-spec.md) for the full feature spec.

- Day view: vertical time-axis (top to bottom), horizontal stage-axis. Each set is a card spanning its time range on its stage's column.
- Week / agenda view: list-of-acts per day, easier on small screens.
- Filter by stage (toggle stages on/off).
- "Today" jump-to-now control.
- Conflict highlighting on the user's own picks.

### 5.3 Friends List / Group View

See [`features/friends-list-spec.md`](features/friends-list-spec.md) for the full feature spec.

- Top-bar avatars for every group member; tap one to see their full pick list.
- Each set card on the calendar shows which members are going (small colored dots).
- Time-of-day "where is everyone right now?" view: for the current (or selected) moment, show every member and which set they're at.

### 5.4 Artist Drill-Down

See [`features/artist-drilldown-spec.md`](features/artist-drilldown-spec.md) for the full feature spec.

- Tap an artist on the calendar → modal opens with:
  - Artist photo (Spotify).
  - Genre tags (Spotify).
  - Similar artists (Spotify's `related-artists` was deprecated in late 2024 — fallback chain documented in [`decisions/ADR-005-music-data-source.md`](decisions/ADR-005-music-data-source.md)).
  - Top track preview (30-second clip from Spotify's `top-tracks` endpoint, with link to open in Spotify).
- Backend handles all music-data API calls; frontend never sees the API key.
- Responses cached for 7 days per artist (artists rarely change).

### 5.5 Setlist Import

- File-based: a JSON file matching the schema is loaded at app start.
- Admin endpoint (auth-gated by a long-lived admin token): paste new JSON into a running deploy without redeploying.
- Validation against the Pydantic model; clear error messages for malformed input.

### 5.6 Offline Mode

- Service worker caches static assets + the lineup JSON.
- Pick mutations queue in IndexedDB when offline.
- On reconnect: queue flushes to the API with last-write-wins reconciliation.
- "Offline" indicator in the UI when network is down.
- Stale-data warning if group state hasn't refetched in > 4 hours.

## 6. User Flows

### Creating a group
```
Open site → "Create group" → name it → get shareable link → share with friends.
```

### Joining a group
```
Open shared link → enter display name → land on the calendar.
```

### Picking sets
```
Browse day/stage on the calendar → tap a set → added to your picks
→ friends see your name on that set in the group view.
```

### Looking up an artist
```
Tap artist on calendar → modal opens with genre + similar artists + top track preview.
```

### Offline at the venue
```
At venue with no signal → tap to pick → queued locally
→ Wi-Fi briefly reconnects → queue flushes → group state syncs.
```

## 7. Technical Considerations

| Area | Consideration |
|---|---|
| PWA install | Manifest + service worker; "Add to Home Screen" prompt on iOS Safari + Android Chrome. |
| Service worker strategy | Cache-first for lineup + static assets; network-first for group state with stale-while-revalidate. |
| Offline queue | IndexedDB write queue keyed by `(group_code, member_id, set_id, action_timestamp)`. Last-write-wins on reconnect. |
| Backend | FastAPI + SQLite (single file; easy single-disk deploy on Render with persistent disk attached). |
| External APIs | Spotify Web API for artist data (backend-only; client credentials flow). See [ADR-005](decisions/ADR-005-music-data-source.md). |
| Group code | 8-character base32 (Crockford alphabet); ~1.1T unique codes. |
| Data privacy | No PII beyond display name + group code. No tracking. |
| Hosting | Render web service (FastAPI) + Render Static Site or Vercel (Next.js). |
| Scale plan | SQLite is fine to ~10k concurrent groups; migrate to Postgres only if pain emerges. |

## 8. Open Questions

1. Should the group code be re-usable across events (one group, multiple events)? Defer to v2 — v1 is one group ↔ one event.
2. Push notifications: any value at v1, or stick to polling? Defer to v2.
3. Display-name uniqueness within a group: enforce, or allow duplicates with a numeric suffix? Defer — most groups will self-police.
4. Group moderator: should the creator have extra privileges (kick, rename group)? Defer — v1 is fully cooperative.
5. Lineup data source policy for the public repo: ship example data only; specific real events require a per-event decision. Captured in [CONTRIBUTING.md](../CONTRIBUTING.md).
6. Spotify API quota strategy when caching expires en masse at the start of a popular event: pre-warm the cache, or backoff and accept slow first-load? Captured in [ADR-005](decisions/ADR-005-music-data-source.md).

## 9. Roadmap

See [`ROADMAP.md`](ROADMAP.md).
