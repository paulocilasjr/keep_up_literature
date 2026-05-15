from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ResearchFieldBase(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None
    keywords: list[str] = Field(default_factory=list)
    pubmed_query: str | None = None
    is_active: bool = True

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("At least one keyword or context is required.")
        return cleaned


class ResearchFieldCreate(ResearchFieldBase):
    pass


class ResearchFieldUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    description: str | None = None
    keywords: list[str] | None = None
    pubmed_query: str | None = None
    is_active: bool | None = None

    @field_validator("keywords")
    @classmethod
    def clean_keywords(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        cleaned = [item.strip() for item in value if item.strip()]
        if not cleaned:
            raise ValueError("At least one keyword or context is required.")
        return cleaned


class ResearchFieldRead(BaseModel):
    id: int
    name: str
    description: str | None
    keywords: list[str]
    pubmed_query: str
    is_active: bool
    created_at: datetime
    updated_at: datetime
    unread_count: int = 0
    paper_count: int = 0

    model_config = ConfigDict(from_attributes=True)
