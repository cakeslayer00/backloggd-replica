from sqlalchemy import String, Text, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    release_year: Mapped[int | None] = mapped_column(Integer)
    cover_image_url: Mapped[str | None] = mapped_column(String(500))

    platforms: Mapped[list["GamePlatform"]] = relationship(back_populates="game")
    backlog_entries: Mapped[list["BacklogEntry"]] = relationship(back_populates="game")
    reviews: Mapped[list["Review"]] = relationship(back_populates="game")


class GamePlatform(Base):
    __tablename__ = "game_platforms"

    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), primary_key=True)
    platform_id: Mapped[int] = mapped_column(
        ForeignKey("platforms.id"), primary_key=True
    )

    game: Mapped["Game"] = relationship(back_populates="platforms")
    platform: Mapped["Platform"] = relationship(back_populates="games")
