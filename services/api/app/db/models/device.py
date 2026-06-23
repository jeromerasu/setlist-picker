from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TIMESTAMPTZ, Base
from app.db.uuid7 import uuid7


class Device(Base):
    __tablename__ = "device"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid7)
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=False,
    )
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    push_token: Mapped[str] = mapped_column(Text, nullable=False)
    push_provider: Mapped[str] = mapped_column(Text, nullable=False, default="expo")
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    revoked_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
