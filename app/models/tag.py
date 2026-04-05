from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    created_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    created_by: Mapped["User"] = relationship()
    entries: Mapped[list["BacklogEntryTag"]] = relationship(back_populates="tag")