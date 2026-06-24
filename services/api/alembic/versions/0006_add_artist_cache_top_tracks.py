"""Add top_tracks JSONB column to artist_cache for multi-track Spotify response.

Revision ID: 0006_add_artist_cache_top_tracks
Revises: 0005_add_stage_color
Create Date: 2026-06-25
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB  # noqa: F401

from alembic import op

revision = "0006_add_artist_cache_top_tracks"
down_revision = "0005_add_stage_color"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artist_cache",
        sa.Column("top_tracks", JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("artist_cache", "top_tracks")
