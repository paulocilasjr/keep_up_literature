from __future__ import annotations

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.paper import Paper
from app.models.research_field import ResearchField
from app.schemas.research_field import ResearchFieldCreate, ResearchFieldUpdate
from app.services.query_builder import PubMedQueryBuilder


class ResearchFieldRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list(self) -> list[ResearchField]:
        statement = select(ResearchField).order_by(ResearchField.created_at.desc())
        return list(self.db.scalars(statement))

    def list_active(self) -> list[ResearchField]:
        statement = select(ResearchField).where(ResearchField.is_active.is_(True)).order_by(ResearchField.name)
        return list(self.db.scalars(statement))

    def get(self, field_id: int) -> ResearchField | None:
        return self.db.get(ResearchField, field_id)

    def get_counts(self) -> dict[int, tuple[int, int]]:
        in_queue = Paper.is_archived.is_(False) & Paper.discarded_at.is_(None)
        unread = func.sum(case((in_queue & Paper.is_read.is_(False), 1), else_=0))
        paper_count = func.sum(case((in_queue, 1), else_=0))
        statement = select(Paper.research_field_id, paper_count, unread).group_by(Paper.research_field_id)
        counts: dict[int, tuple[int, int]] = {}
        for field_id, paper_count, unread_count in self.db.execute(statement):
            counts[field_id] = (int(paper_count or 0), int(unread_count or 0))
        return counts

    def create(self, payload: ResearchFieldCreate) -> ResearchField:
        query = payload.pubmed_query or PubMedQueryBuilder.build(
            payload.keywords,
            name=payload.name,
            description=payload.description,
        )
        field = ResearchField(
            name=payload.name,
            description=payload.description,
            keywords=payload.keywords,
            pubmed_query=query,
            is_active=payload.is_active,
        )
        self.db.add(field)
        self.db.commit()
        self.db.refresh(field)
        return field

    def update(self, field: ResearchField, payload: ResearchFieldUpdate) -> ResearchField:
        changes = payload.model_dump(exclude_unset=True)
        query_inputs_changed = any(key in changes for key in ("keywords", "name", "description"))
        if query_inputs_changed and "pubmed_query" not in changes:
            changes["pubmed_query"] = PubMedQueryBuilder.build(
                changes.get("keywords", field.keywords),
                name=changes.get("name", field.name),
                description=changes.get("description", field.description),
            )
        for key, value in changes.items():
            setattr(field, key, value)
        self.db.commit()
        self.db.refresh(field)
        return field

    def delete(self, field: ResearchField) -> None:
        self.db.delete(field)
        self.db.commit()

    def record_sync_success(self, field: ResearchField, synced_at: datetime) -> None:
        field.last_synced_at = synced_at
        field.last_sync_status = "success"
        field.last_sync_error = None

    def record_sync_failure(self, field: ResearchField, message: str) -> None:
        field.last_sync_status = "error"
        field.last_sync_error = message[:2_000]
        self.db.commit()
