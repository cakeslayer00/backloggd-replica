from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class BacklogEntryTag(Base):
    __tablename__ = "backlog_entry_tags"

    entry_id: Mapped[int] = mapped_column(ForeignKey("backlog_entries.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)

    entry: Mapped["BacklogEntry"] = relationship(back_populates="tags")
    tag: Mapped["Tag"] = relationship(back_populates="entries")