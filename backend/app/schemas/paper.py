from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PaperRead(BaseModel):
    id: int
    research_field_id: int
    pubmed_id: str
    journal_name: str | None
    publication_date: date | None
    author_list: list[str]
    publication_types: list[str]
    title: str
    abstract: str | None
    link: str
    priority_score: float
    priority_label: str
    priority_reasons: list[str]
    is_read: bool
    is_starred: bool
    is_archived: bool
    notes: str | None
    discarded_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaperStatusUpdate(BaseModel):
    is_read: bool | None = None
    is_starred: bool | None = None
    is_archived: bool | None = None
    notes: str | None = Field(default=None, max_length=20_000)

    @model_validator(mode="after")
    def require_change(self) -> "PaperStatusUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one paper change is required.")
        return self


class SyncResult(BaseModel):
    research_field_id: int | None = None
    fetched: int
    inserted: int
    skipped_irrelevant: int
    skipped_existing: int
    skipped_deleted: int
    skipped_outside_current_day: int
    sync_from: date | None = None
    sync_to: date | None = None
