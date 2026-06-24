"""Add color_hex column to stage table and backfill existing rows.

Assigns each stage a display color from the 15-entry REALIGN-001 palette,
deterministically by position within the event's stage list (ordered by
display_order). New stages are assigned by the importer using display_order % 15.

Revision ID: 0005_add_stage_color
Revises: 0004_fix_tml_w2_event_adapter
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0005_add_stage_color"
down_revision = "0004_fix_tml_w2_event_adapter"
branch_labels = None
depends_on = None

# 15-entry palette matching _STAGE_COLORS in lineup_import_service.py.
# Index order must stay in sync with that constant.
_PALETTE = [
    (0, "#ff4f9a"),
    (1, "#36c6ff"),
    (2, "#a06bff"),
    (3, "#2dd4bf"),
    (4, "#ffd23f"),
    (5, "#ff6a3d"),
    (6, "#ff2d9b"),
    (7, "#28e0ff"),
    (8, "#a78bfa"),
    (9, "#7b5cff"),
    (10, "#0e7c66"),
    (11, "#5b1bd6"),
    (12, "#ff8ad6"),
    (13, "#1453d6"),
    (14, "#cdb4fe"),
]

_PALETTE_VALUES = ", ".join(f"({idx}, '{hex_}')" for idx, hex_ in _PALETTE)


def upgrade() -> None:
    # Step 1: add column with a temporary server default so existing rows satisfy NOT NULL.
    op.add_column(
        "stage",
        sa.Column("color_hex", sa.Text, nullable=False, server_default="#a78bfa"),
    )

    # Step 2: backfill all existing rows.
    # ROW_NUMBER (per event, ordered by display_order) gives a stable 0-based index
    # regardless of the actual display_order values, guaranteeing 15 distinct colors
    # across the existing 15 Tomorrowland stages.
    op.execute(
        sa.text(
            f"""
            WITH ranked AS (
                SELECT
                    stage_id,
                    ((ROW_NUMBER() OVER (
                        PARTITION BY event_id ORDER BY display_order
                    ) - 1) % 15)::int AS color_idx
                FROM stage
            ),
            palette AS (
                SELECT *
                FROM (VALUES {_PALETTE_VALUES}) AS t(color_idx, hex)
            )
            UPDATE stage
            SET color_hex = palette.hex
            FROM ranked
            JOIN palette ON palette.color_idx = ranked.color_idx
            WHERE stage.stage_id = ranked.stage_id
            """
        )
    )

    # Step 3: drop the server default — all new rows must be supplied by the importer.
    op.alter_column("stage", "color_hex", server_default=None)


def downgrade() -> None:
    op.drop_column("stage", "color_hex")
