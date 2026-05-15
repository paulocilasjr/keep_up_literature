from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PaperRead(BaseModel):
    id: int
    research_field_id: int
    pubmed_id: str
    journal_name: str | None
    publication_date: date | None
    author_list: list[str]
    title: str
    abstract: str | None
    link: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperStatusUpdate(BaseModel):
    is_read: bool


class SyncResult(BaseModel):
    research_field_id: int | None = None
    fetched: int
    inserted: int
    skipped_existing: int
    skipped_outside_current_month: int
