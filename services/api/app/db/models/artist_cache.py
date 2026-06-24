from __future__ import annotations

from datetime import datetime

from sqlalchemy import Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import TIMESTAMPTZ, Base


class ArtistCache(Base):
    __tablename__ = "artist_cache"

    name_normalized: Mapped[str] = mapped_column(Text, primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)
    spotify_artist_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    similar_artists: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB, nullable=True)
    top_track: Mapped[dict[str, object] | None] = mapped_column(JSONB, nullable=True)
    top_tracks: Mapped[list[dict[str, object]] | None] = mapped_column(JSONB, nullable=True)
    similarity_source: Mapped[str | None] = mapped_column(Text, nullable=True)
    fetched_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
    fetch_failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_failure_at: Mapped[datetime | None] = mapped_column(TIMESTAMPTZ, nullable=True)
