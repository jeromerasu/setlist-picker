"""AUTH-EMAIL-AS-USERNAME: drop username column, enforce email as local-auth identifier.

Revision ID: 0002_auth_email_as_username
Revises: 0001_v001_baseline
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0002_auth_email_as_username"
down_revision = "0001_v001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop partial unique index on username, then the column.
    op.drop_index("uq_user_username", table_name="user")
    op.drop_column("user", "username")

    # Replace the existing partial unique index on email (email IS NOT NULL)
    # with a case-insensitive one on LOWER(email).
    op.drop_index("uq_user_email", table_name="user")
    op.execute(
        sa.text(
            'CREATE UNIQUE INDEX uq_user_email_lower ON "user" (LOWER(email))'
            " WHERE email IS NOT NULL"
        )
    )

    # Basic format check at the DB layer; NULL satisfies this automatically
    # because PostgreSQL CHECK treats NULL result as not-false.
    op.execute(
        sa.text(
            "ALTER TABLE \"user\" ADD CONSTRAINT ck_user_email_format"
            " CHECK (email ~* '^[^@]+@[^@]+\\.[^@]+$')"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text('ALTER TABLE "user" DROP CONSTRAINT ck_user_email_format')
    )
    op.drop_index("uq_user_email_lower", table_name="user")
    op.create_index(
        "uq_user_email",
        "user",
        ["email"],
        unique=True,
        postgresql_where=sa.text("email IS NOT NULL"),
    )
    op.add_column("user", sa.Column("username", sa.Text(), nullable=True))
    op.create_index(
        "uq_user_username",
        "user",
        ["username"],
        unique=True,
        postgresql_where=sa.text("username IS NOT NULL"),
    )
