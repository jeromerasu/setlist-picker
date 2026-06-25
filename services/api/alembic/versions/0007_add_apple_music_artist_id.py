"""SETLIST-APPLE-MUSIC-INTEGRATION: add apple_music_artist_id to artist_cache.

Revision ID: 0007_add_apple_music_artist_id
Revises: 0006_add_artist_cache_top_tracks
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0007_add_apple_music_artist_id"
down_revision = "0006_add_artist_cache_top_tracks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "artist_cache",
        sa.Column("apple_music_artist_id", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("artist_cache", "apple_music_artist_id")
