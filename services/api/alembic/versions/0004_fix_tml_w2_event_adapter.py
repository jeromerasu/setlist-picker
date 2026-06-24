"""FIX: Correct source_adapter and external_id on the Tomorrowland W2 event row.

Migration 0003 seeded the event with source_adapter='manual' and external_id=NULL.
The canonical source is .local-data/tml26-w2.json and the import path is
scripts/import_lineup.py with --source-adapter event_api_v1 --external-id tml-2026-w2.

This migration corrects the two fields so that a subsequent run of import_lineup.py
will upsert onto the existing row (via uq_event_external) rather than creating a
duplicate event in the dropdown.

Revision ID: 0004_fix_tml_w2_event_adapter
Revises: 0003_seed_tomorrowland_w2
Create Date: 2026-06-24
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0004_fix_tml_w2_event_adapter"
down_revision = "0003_seed_tomorrowland_w2"
branch_labels = None
depends_on = None

_EVENT_ID = "8028c52c-219e-4b55-83bb-c5318830afbc"


def upgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE event
            SET source_adapter = 'event_api_v1',
                external_id    = 'tml-2026-w2'
            WHERE event_id = '{_EVENT_ID}'::uuid
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE event
            SET source_adapter = 'manual',
                external_id    = NULL
            WHERE event_id = '{_EVENT_ID}'::uuid
            """
        )
    )
