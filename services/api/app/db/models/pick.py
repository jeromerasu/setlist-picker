from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TIMESTAMPTZ, Base


class Pick(Base):
    __tablename__ = "pick"

    member_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("member.id", ondelete="CASCADE"),
        primary_key=True,
    )
    set_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("set.set_id", ondelete="CASCADE"),
        primary_key=True,
    )
    state: Mapped[str] = mapped_column(Text, nullable=False, default="active")
    state_clock_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    server_first_seen_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
    server_last_updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )
