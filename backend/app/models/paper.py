from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Paper(Base):
    __tablename__ = "papers"
    __table_args__ = (UniqueConstraint("research_field_id", "pubmed_id", name="uq_field_pubmed_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    research_field_id: Mapped[int] = mapped_column(ForeignKey("research_fields.id", ondelete="CASCADE"), index=True)
    pubmed_id: Mapped[str] = mapped_column(String(32), index=True)
    journal_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    author_list: Mapped[list[str]] = mapped_column(JSON, default=list)
    publication_types: Mapped[list[str]] = mapped_column(JSON, default=list)
    title: Mapped[str] = mapped_column(Text)
    abstract: Mapped[str | None] = mapped_column(Text, nullable=True)
    link: Mapped[str] = mapped_column(String(255))
    priority_score: Mapped[float] = mapped_column(Float, default=0.0, index=True)
    priority_label: Mapped[str] = mapped_column(String(40), default="Standard")
    priority_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_starred: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    discarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    research_field = relationship("ResearchField", back_populates="papers")
