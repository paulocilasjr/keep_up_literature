from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeletedPaper(Base):
    __tablename__ = "deleted_papers"
    __table_args__ = (UniqueConstraint("research_field_id", "pubmed_id", name="uq_deleted_field_pubmed_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    research_field_id: Mapped[int] = mapped_column(ForeignKey("research_fields.id", ondelete="CASCADE"), index=True)
    pubmed_id: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    publication_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    deleted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    research_field = relationship("ResearchField", back_populates="deleted_papers")
