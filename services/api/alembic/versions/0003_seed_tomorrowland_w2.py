"""SEED: Tomorrowland 2026 Weekend 2 event row.

Revision ID: 0003_seed_tomorrowland_w2
Revises: 0002_auth_email_as_username
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0003_seed_tomorrowland_w2"
down_revision = "0002_auth_email_as_username"
branch_labels = None
depends_on = None

_EVENT_ID = "8028c52c-219e-4b55-83bb-c5318830afbc"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            INSERT INTO event
                (event_id, name, start_date, end_date, location, timezone, source_adapter)
            VALUES (
                '{_EVENT_ID}'::uuid,
                'Tomorrowland 2026 — Weekend 2',
                '2026-07-24',
                '2026-07-26',
                'Boom, Belgium',
                'Europe/Brussels',
                'manual'
            )
            ON CONFLICT (event_id) DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(f"DELETE FROM event WHERE event_id = '{_EVENT_ID}'::uuid")
    )
