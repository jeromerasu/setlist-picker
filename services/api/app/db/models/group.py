from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CHAR, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TIMESTAMPTZ, Base
from app.db.uuid7 import uuid7


class Group(Base):
    __tablename__ = "group"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    name: Mapped[str] = mapped_column(Text, nullable=False, default="Friends 🎵")
    invite_code: Mapped[str] = mapped_column(CHAR(8), nullable=False)
    event_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("event.event_id", ondelete="CASCADE"),
        nullable=False,
    )
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    last_active_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
