# REALIGN-005 — BE: Group-aggregated schedule endpoint

## Goal

Add `GET /api/groups/{invite_code}/schedule` — a new endpoint that returns every set for a given day, annotated with which group members have active picks (going). This powers the Schedule > **Group** filter view in REALIGN-002, where the timeline shows sets that any group member is attending, with their avatars stacked on each card.

The existing `GroupStateResponse` from `GET /api/groups/{invite_code}` returns a flat `picks` list, which forces the client to do O(members × sets) matching locally and join against the lineup data separately. The new endpoint collapses that into a single, shaped response.

## Source of truth

- Prototype data shape: `v.groupSets` computation (line 704–706 in `docs/design/FestApp.dc.html`)
  ```js
  const grp = this.SETS.filter(s => s.day === st.schedDay && this.goingMembers(s).length > 0)
                       .sort((a,b) => a.start - b.start)
  v.groupSets = grp.map(s => {
    const gm = this.goingMembers(s)
    return { artist, sLabel, eLabel, stage, color, goingLabel: gm.length + ' going',
             going: gm.map(m => ({i: m.i, c: m.c, t: m.t})) }
  })
  ```
- Locked: only **active** picks (`state = "active"`) count as "going". Tombstoned picks are excluded.
- Existing route structure: `services/api/app/routes/groups.py` — add the new endpoint here.
- Existing service: `services/api/app/services/group_service.py` — add a new service function.
- Existing schemas: `services/api/app/schemas/groups.py` — add new schemas.
- Prerequisite: REALIGN-001 must land first (stage.color_hex needed in response).

## API contract

### Endpoint

```
GET /api/groups/{invite_code}/schedule?day_label={day_label}
Authorization: Bearer {token}
```

`day_label` is a required query parameter. It matches the `Set.day_label` column exactly (e.g., `"Day 1"`, `"Friday"`, `"2026-07-24"` — whatever string the importer wrote). No normalization is performed by this endpoint.

### Response: `GroupScheduleResponse`

```python
class MemberPickInfo(_Model):
    member_id: UUID
    display_name: str
    avatar_color: str

class GroupSetItem(_Model):
    set_id: UUID
    display_name: str
    stage_name: str
    stage_color_hex: str
    day_label: str
    starts_at: datetime
    ends_at: datetime
    going_members: list[MemberPickInfo]

class GroupScheduleResponse(_Model):
    group_id: UUID
    event_id: UUID
    day_label: str
    sets: list[GroupSetItem]
```

- `sets` contains **only sets where at least one group member has an active pick** (`going_members` is non-empty).
- `sets` is sorted by `starts_at` ascending.
- `going_members` lists all group members with an active pick on this set, sorted by `joined_at` ascending (first joiner first).
- `stage_color_hex` comes from `Stage.color_hex` (added by REALIGN-001).

**No `maybe_members` field.** The group timeline view (prototype line 704) only shows sets where members are "going" (active picks). Maybe-state picks do not appear in the group timeline.

### Error responses

| Condition | HTTP status | `detail.error_code` |
|-----------|-------------|---------------------|
| Group not found | 404 | `group_not_found` |
| Caller is not a member of the group | 403 | `not_a_member` |
| `day_label` query param missing | 422 | FastAPI validation default |
| No sets for this day_label | 200 | (empty `sets: []`) |

### Example response

```json
{
  "group_id": "...",
  "event_id": "...",
  "day_label": "Day 1",
  "sets": [
    {
      "set_id": "...",
      "display_name": "Vintage Culture",
      "stage_name": "Mainstage",
      "stage_color_hex": "#ff4f9a",
      "day_label": "Day 1",
      "starts_at": "2026-07-24T14:00:00+02:00",
      "ends_at": "2026-07-24T15:30:00+02:00",
      "going_members": [
        {
          "member_id": "...",
          "display_name": "Jerome",
          "avatar_color": "#a78bfa"
        }
      ]
    }
  ]
}
```

## Scope

### Schema — `services/api/app/schemas/groups.py`

Add the three new Pydantic models: `MemberPickInfo`, `GroupSetItem`, `GroupScheduleResponse`.

### Service — `services/api/app/services/group_service.py`

Add `get_group_schedule(db, caller, invite_code, day_label) -> GroupScheduleResponse`.

Query pattern (single round-trip with joins):

```sql
SELECT
    s.set_id, s.display_name, s.day_label, s.starts_at, s.ends_at,
    st.name AS stage_name, st.color_hex AS stage_color_hex,
    m.member_id, m.display_name AS member_display_name, m.avatar_color,
    m.joined_at
FROM pick p
JOIN "set" s  ON s.set_id  = p.set_id
JOIN stage st ON st.stage_id = s.stage_id
JOIN member m ON m.member_id = p.member_id
WHERE m.group_id = :group_id
  AND s.day_label = :day_label
  AND p.state = 'active'
ORDER BY s.starts_at ASC, m.joined_at ASC
```

Aggregate in Python: iterate rows, group by `set_id`, build `GroupSetItem` list. Only sets with `len(going_members) > 0` are included (the WHERE clause already ensures this).

Caller membership check: before running the main query, verify that the caller (authenticated user) has a `Member` row for this group. If not, raise HTTP 403 with `{"error_code": "not_a_member"}`.

Structured logging: log at INFO level on success with `group_id`, `day_label`, `set_count`, `total_picks`. Use `logger.exception(...)` for unexpected errors.

### Route — `services/api/app/routes/groups.py`

```python
@router.get("/{invite_code}/schedule", response_model=GroupScheduleResponse)
async def get_group_schedule_endpoint(
    invite_code: str,
    day_label: str = Query(...),
    caller: Annotated[User, Depends(current_user)] = ...,
    db: AsyncSession = Depends(get_db),
) -> GroupScheduleResponse:
    group = await _resolve_group(invite_code, db)
    return await get_group_schedule(db, caller, group, day_label)
```

The `_resolve_group` helper already exists in `groups.py` — reuse it.

## Tests

Add tests in `services/api/tests/` (wherever existing route tests live):
- Returns correct sets for a day with active picks.
- Excludes sets with no active picks.
- Excludes tombstoned picks.
- Returns 403 when caller is not a member.
- Returns empty `sets: []` (not 404) when `day_label` has no picks.
- `going_members` sorted by `joined_at` ascending.

## Acceptance criteria

- [ ] `GET /api/groups/{code}/schedule?day_label=Day+1` returns only sets with `going_members.length > 0`.
- [ ] Tombstoned picks excluded from `going_members`.
- [ ] Non-member caller receives 403.
- [ ] Response includes `stage_color_hex` from REALIGN-001 migration.
- [ ] `sets` sorted by `starts_at`.
- [ ] `going_members` sorted by `joined_at`.
- [ ] `pytest` green (including new tests).
- [ ] `mypy --strict` clean.
- [ ] `ruff check .` clean.

## Out of scope

- "Mine" filter data (already available from `GroupStateResponse.picks` — no new endpoint needed).
- Member filtering (selecting individual members in the group timeline filter sheet) — the client filters `going_members` locally by the selected member IDs from the filter sheet.
- Caching / ETag headers (add in a follow-up if polling pressure warrants it).
