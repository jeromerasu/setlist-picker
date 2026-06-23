"""V001 baseline — all 13 tables + 26 indexes per ADR-006.

Revision ID: 0001_v001_baseline
Revises:
Create Date: 2026-06-23
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0001_v001_baseline"
down_revision: None = None
branch_labels: None = None
depends_on: None = None


def upgrade() -> None:
    # 1. user
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("auth_provider", sa.Text(), nullable=False, server_default="local"),
        sa.Column("username", sa.Text(), nullable=True),
        sa.Column("email", sa.Text(), nullable=True),
        sa.Column("password_hash", sa.Text(), nullable=True),
        sa.Column("apple_subject_id", sa.Text(), nullable=True),
        sa.Column("google_subject_id", sa.Text(), nullable=True),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("avatar_color", sa.CHAR(7), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. event
    op.create_table(
        "event",
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("location", sa.Text(), nullable=True),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="UTC"),
        sa.Column("source_adapter", sa.Text(), nullable=False, server_default="manual"),
        sa.Column("external_id", sa.Text(), nullable=True),
        sa.Column(
            "imported_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id"),
    )

    # 3. group (FK → event, user)
    op.create_table(
        "group",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False, server_default="Friends 🎵"),
        sa.Column("invite_code", sa.CHAR(8), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_active_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["event_id"], ["event.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["user.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 4. member (FK → user, group)
    op.create_table(
        "member",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name_override", sa.Text(), nullable=True),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["group_id"], ["group.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. device (FK → user)
    op.create_table(
        "device",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("push_token", sa.Text(), nullable=False),
        sa.Column("push_provider", sa.Text(), nullable=False, server_default="expo"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 6. stage (FK → event)
    op.create_table(
        "stage",
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["event.event_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("stage_id"),
    )

    # 7. set (FK → event, stage)
    op.create_table(
        "set",
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("day_label", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["event_id"], ["event.event_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["stage_id"], ["stage.stage_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("set_id"),
    )

    # 8. artist
    op.create_table(
        "artist",
        sa.Column("artist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("name_normalized", sa.Text(), nullable=False),
        sa.Column("spotify_artist_id", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("social_links", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("artist_id"),
    )

    # 9. artist_source_ref (FK → artist)
    op.create_table(
        "artist_source_ref",
        sa.Column("artist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_adapter", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["artist_id"], ["artist.artist_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("artist_id", "source_adapter"),
    )

    # 10. set_artist (FK → set, artist)
    op.create_table(
        "set_artist",
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artist_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["set_id"], ["set.set_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["artist_id"], ["artist.artist_id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("set_id", "artist_id"),
    )

    # 11. pick (FK → member, set)
    op.create_table(
        "pick",
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("set_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("state", sa.Text(), nullable=False, server_default="active"),
        sa.Column("state_clock_ms", sa.BigInteger(), nullable=False),
        sa.Column(
            "server_first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "server_last_updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["set_id"], ["set.set_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("member_id", "set_id"),
    )

    # 12. artist_cache (PK = name_normalized)
    op.create_table(
        "artist_cache",
        sa.Column("name_normalized", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("spotify_artist_id", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("genres", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("similar_artists", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("top_track", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("similarity_source", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fetch_failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("name_normalized"),
    )

    # 13. group_activity (FK → group, member SET NULL)
    op.create_table(
        "group_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("member_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("kind", sa.Text(), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["group_id"], ["group.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["member_id"], ["member.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── 26 indexes from ADR-006 § 3 ─────────────────────────────────────────

    # user indexes
    op.create_index(
        "uq_user_username",
        "user",
        ["username"],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )
    op.create_index(
        "uq_user_email",
        "user",
        ["email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.create_index(
        "uq_user_apple_subject",
        "user",
        ["apple_subject_id"],
        unique=True,
        postgresql_where=sa.text("apple_subject_id IS NOT NULL"),
    )
    op.create_index(
        "uq_user_google_subject",
        "user",
        ["google_subject_id"],
        unique=True,
        postgresql_where=sa.text("google_subject_id IS NOT NULL"),
    )

    # group indexes
    op.create_index("uq_group_invite_code", "group", ["invite_code"], unique=True)
    op.create_index(
        "idx_group_archive_sweep",
        "group",
        ["last_active_at"],
        postgresql_where=sa.text("archived_at IS NULL"),
    )
    op.create_index("idx_group_event", "group", ["event_id"])

    # member indexes
    op.create_index("uq_member_user_group", "member", ["user_id", "group_id"], unique=True)
    op.create_index("idx_member_group", "member", ["group_id"])
    op.create_index("idx_member_user", "member", ["user_id"])

    # device indexes
    op.create_index("uq_device_user_token", "device", ["user_id", "push_token"], unique=True)
    op.create_index(
        "idx_device_user_active",
        "device",
        ["user_id"],
        postgresql_where=sa.text("revoked_at IS NULL"),
    )

    # event indexes
    op.create_index(
        "uq_event_external",
        "event",
        ["source_adapter", "external_id"],
        unique=True,
        postgresql_where=sa.text("external_id IS NOT NULL"),
    )

    # stage indexes
    op.create_index("uq_stage_external", "stage", ["event_id", "external_id"], unique=True)
    op.create_index("idx_stage_event_order", "stage", ["event_id", "display_order"])

    # set indexes
    op.create_index("uq_set_external", "set", ["event_id", "external_id"], unique=True)
    op.create_index("idx_set_event_starts", "set", ["event_id", "starts_at"])
    op.create_index("idx_set_stage_starts", "set", ["stage_id", "starts_at"])

    # artist indexes
    op.create_index("uq_artist_name_normalized", "artist", ["name_normalized"], unique=True)
    op.create_index(
        "idx_artist_spotify",
        "artist",
        ["spotify_artist_id"],
        postgresql_where=sa.text("spotify_artist_id IS NOT NULL"),
    )

    # artist_source_ref indexes
    op.create_index(
        "uq_artist_source_ext",
        "artist_source_ref",
        ["source_adapter", "external_id"],
        unique=True,
    )

    # set_artist indexes
    op.create_index("idx_setartist_artist", "set_artist", ["artist_id"])
    op.create_index("uq_set_position", "set_artist", ["set_id", "position"], unique=True)

    # pick indexes
    op.create_index(
        "idx_pick_set_active",
        "pick",
        ["set_id"],
        postgresql_where=sa.text("state = 'active'"),
    )
    op.create_index(
        "idx_pick_member_active",
        "pick",
        ["member_id"],
        postgresql_where=sa.text("state = 'active'"),
    )

    # artist_cache indexes
    op.create_index(
        "idx_artist_cache_fetched",
        "artist_cache",
        ["fetched_at"],
        postgresql_where=sa.text("fetched_at IS NOT NULL"),
    )

    # group_activity indexes
    op.create_index(
        "idx_group_activity_group_time",
        "group_activity",
        ["group_id", sa.text("created_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("group_activity")
    op.drop_table("artist_cache")
    op.drop_table("pick")
    op.drop_table("set_artist")
    op.drop_table("artist_source_ref")
    op.drop_table("artist")
    op.drop_table("set")
    op.drop_table("stage")
    op.drop_table("device")
    op.drop_table("member")
    op.drop_table("group")
    op.drop_table("event")
    op.drop_table("user")
