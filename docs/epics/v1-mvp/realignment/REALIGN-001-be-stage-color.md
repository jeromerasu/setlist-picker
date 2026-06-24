# REALIGN-001 — BE: Stage color column + 15-color palette

## Goal

Add a `color_hex` column to the `stage` table so each stage carries its display color in the database, assigned deterministically at import time by cycling through a 15-color palette. Surface `color_hex` in the `StageDetail` API schema. This unblocks REALIGN-002 and REALIGN-003, which need per-stage colors from the API.

## Source of truth

- Stage dot colors in prototype: `docs/design/FestApp.dc.html` lines 492–494 (4 hardcoded Lost Lands colors).
- Rotation pattern: `this.HUES[i % this.HUES.length]` at line 614 — the importer must follow the same modulo-on-`display_order` pattern.
- Locked design decision: 15 distinct hues, no repeats across Tomorrowland's 15 stages (IMPLEMENTATION-GUIDE.md § locked decisions #3).
- Existing DB model: `services/api/app/db/models/stage.py` — no `color_hex` column today.
- Existing API schema: `services/api/app/schemas/events.py` — `StageDetail` lacks `color_hex`.
- Existing importer: `services/api/scripts/import_lineup.py` → `services/api/app/services/lineup_import_service.py` — assigns `display_order` but not `color_hex`.

## 15-color stage palette (canonical, ordered)

All values grounded in `docs/epics/v1-mvp/DESIGN-TOKENS.md`. Assign to stages by `display_order % 15`.

| Index | Hex | Source in tokens |
|-------|-----|-----------------|
| 0 | `#ff4f9a` | `stage.sherwood` |
| 1 | `#36c6ff` | `stage.tripolee` |
| 2 | `#a06bff` | `stage.ranch` |
| 3 | `#2dd4bf` | `stage.cosmic` |
| 4 | `#ffd23f` | HUES[4] amber start |
| 5 | `#ff6a3d` | HUES[4] orange end |
| 6 | `#ff2d9b` | `neon.pink` |
| 7 | `#28e0ff` | `neon.cyan` |
| 8 | `#a78bfa` | `neon.purple` |
| 9 | `#7b5cff` | `neon.purpleDeep` |
| 10 | `#0e7c66` | HUES[3] forest end |
| 11 | `#5b1bd6` | `neon.violetSat` |
| 12 | `#ff8ad6` | `text.daySectionAccent` |
| 13 | `#1453d6` | `neon.skyDeep` |
| 14 | `#cdb4fe` | `neon.lilac` |

This palette constant must be defined in `lineup_import_service.py` as a module-level tuple named `_STAGE_COLORS`.

## Scope

### Migration — `services/api/alembic/versions/0005_add_stage_color.py`

- `down_revision = "0004_fix_tml_w2_event_adapter"`
- `upgrade()`:
  1. `ALTER TABLE stage ADD COLUMN color_hex VARCHAR(7) NOT NULL DEFAULT '#a78bfa'` — temporary default so existing rows are valid.
  2. `UPDATE stage SET color_hex = color_table.hex FROM (VALUES ...) AS color_table(disp, hex) WHERE stage.display_order % 15 = color_table.disp` — backfill all existing stage rows using the 15-color palette.
  3. `ALTER TABLE stage ALTER COLUMN color_hex DROP DEFAULT` — remove the server default.
- `downgrade()`: `ALTER TABLE stage DROP COLUMN color_hex`.

Alternatively, step 1 can use a nullable column with a subsequent `NOT NULL` constraint after backfill; either approach is valid as long as `color_hex` is `NOT NULL` at the end.

### Service — `services/api/app/services/lineup_import_service.py`

- Add module-level constant `_STAGE_COLORS: tuple[str, ...] = (...)` with the 15 hex values above.
- In the `_upsert_stage` function (or wherever `display_order` is set), add `color_hex = _STAGE_COLORS[display_order % len(_STAGE_COLORS)]` to the INSERT/UPDATE.
- Existing `ON CONFLICT` logic for stages: ensure `color_hex` is included in the DO UPDATE SET clause so re-running the importer updates color assignments correctly.

### Schema — `services/api/app/schemas/events.py`

Add `color_hex: str` to `StageDetail`:

```python
class StageDetail(_Model):
    stage_id: UUID
    name: str
    display_order: int
    color_hex: str          # <-- new
    sets: list[SetDetail]
```

No other schema changes required. `EventLineupResponse` already includes `stages: list[StageDetail]` so `color_hex` propagates automatically.

### Model — `services/api/app/db/models/stage.py`

Add `color_hex: Mapped[str] = mapped_column(Text, nullable=False)` with no default (the migration backfills existing rows; all new rows come via importer which always supplies the value).

### Route — `services/api/app/routes/events.py`

The `/api/events/{event_id}/lineup` endpoint that returns `EventLineupResponse` needs no changes beyond the schema update, provided the ORM query eager-loads `Stage.color_hex`. Verify the query selects the column (it should after the model update).

## API contract (no new endpoints)

`GET /api/events/{event_id}/lineup` response — `stages` array items:

```json
{
  "stage_id": "...",
  "name": "Mainstage",
  "display_order": 0,
  "color_hex": "#ff4f9a",
  "sets": [...]
}
```

## States / edge cases

- **Re-import**: running `import_lineup.py` a second time must not change `color_hex` for stages where `display_order` hasn't changed. The DO UPDATE clause handles this correctly as long as `color_hex` is recalculated from `display_order`.
- **> 15 stages on a future event**: palette wraps via `% 15`. Colors repeat but this is expected and acceptable.
- **0 stages**: no-op.

## Acceptance criteria

- [ ] `SELECT color_hex FROM stage LIMIT 5` on the remote DB returns valid 7-char hex strings (non-null, matching the palette above).
- [ ] `GET /api/events/{event_id}/lineup` includes `color_hex` on every stage object.
- [ ] `pytest` passes (including any existing event/lineup route tests).
- [ ] `mypy --strict` passes on `lineup_import_service.py`, `stage.py`, `events.py`.
- [ ] `ruff check .` clean.
- [ ] Tomorrowland's 15 stages each have a distinct `color_hex` (no two stages share the same value for this event).

## Out of scope

- Frontend changes (REALIGN-002, REALIGN-003 consume this data).
- Changing the group-card hero gradient (HUES[]) — that is a separate 6-entry palette for group card backgrounds, not stage colors.
- Light-theme color variants (BACKLOG-001).
