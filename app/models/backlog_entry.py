from sqlalchemy import ForeignKey, Enum as SAEnum, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.models.base import Base


class BacklogStatus(enum.Enum):
    want_to_play = "want_to_play"
    playing = "playing"
    completed = "completed"
    dropped = "dropped"
    on_hold = "on_hold"


class BacklogPriority(enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class BacklogEntry(Base):
    __tablename__ = "backlog_entries"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), index=True)
    status: Mapped[BacklogStatus] = mapped_column(
        SAEnum(BacklogStatus), default=BacklogStatus.want_to_play
    )
    priority: Mapped[BacklogPriority] = mapped_column(
        SAEnum(BacklogPriority), default=BacklogPriority.medium
    )
    hours_played: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="backlog_entries")
    game: Mapped["Game"] = relationship(back_populates="backlog_entries")
    screenshots: Mapped[list["Screenshot"]] = relationship(back_populates="entry")
    tags: Mapped[list["BacklogEntryTag"]] = relationship(back_populates="entry")