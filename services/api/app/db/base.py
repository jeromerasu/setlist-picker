from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.types import DateTime


class Base(DeclarativeBase):
    pass


TIMESTAMPTZ = DateTime(timezone=True)
