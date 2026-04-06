from sqlalchemy import ForeignKey, String, Integer, DateTime, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from datetime import datetime
import enum

from app.models.base import Base


class ScreenshotStatus(enum.Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class Screenshot(Base):
    __tablename__ = "screenshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    entry_id: Mapped[int] = mapped_column(ForeignKey("backlog_entries.id"), index=True)
    file_url: Mapped[str] = mapped_column(String(500))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[ScreenshotStatus] = mapped_column(
        SAEnum(ScreenshotStatus), default=ScreenshotStatus.processing
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    entry: Mapped["BacklogEntry"] = relationship(back_populates="screenshots")
