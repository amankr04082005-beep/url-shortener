from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Url(Base):
    __tablename__ = "urls"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # unique=True creates a unique index, so redirect lookups by code are fast
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True, nullable=False)
    original_url: Mapped[str] = mapped_column(Text, nullable=False)
    click_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    clicks: Mapped[list["Click"]] = relationship(back_populates="url", cascade="all, delete-orphan")


class Click(Base):
    __tablename__ = "clicks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url_id: Mapped[int] = mapped_column(ForeignKey("urls.id"), index=True, nullable=False)
    clicked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    user_agent: Mapped[str | None] = mapped_column(String(255), nullable=True)

    url: Mapped["Url"] = relationship(back_populates="clicks")
