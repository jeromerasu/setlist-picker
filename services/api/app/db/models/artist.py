from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TIMESTAMPTZ, Base
from app.db.uuid7 import uuid7


class Artist(Base):
    __tablename__ = "artist"

    artist_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid7
    )
    name: Mapped[str] = mapped_column(Text, nullable=False)
    name_normalized: Mapped[str] = mapped_column(Text, nullable=False)
    spotify_artist_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_links: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMPTZ, nullable=False, server_default=func.now()
    )


class ArtistSourceRef(Base):
    __tablename__ = "artist_source_ref"

    artist_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("artist.artist_id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_adapter: Mapped[str] = mapped_column(Text, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)


class SetArtist(Base):
    __tablename__ = "set_artist"

    set_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("set.set_id", ondelete="CASCADE"),
        primary_key=True,
    )
    artist_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("artist.artist_id", ondelete="RESTRICT"),
        primary_key=True,
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
