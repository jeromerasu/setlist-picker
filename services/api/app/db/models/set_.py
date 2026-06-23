from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TIMESTAMPTZ, Base
from app.db.uuid7 import uuid7


class Set(Base):
    __tablename__ = "set"

    set_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("event.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    stage_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("stage.stage_id", ondelete="CASCADE"),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    day_label: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    ends_at: Mapped[datetime] = mapped_column(TIMESTAMPTZ, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
