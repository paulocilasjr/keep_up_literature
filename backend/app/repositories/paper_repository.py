from datetime import date, datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.deleted_paper import DeletedPaper
from app.models.paper import Paper
from app.services.priority_scorer import PriorityScore
from app.services.pubmed_client import PubMedArticle


class PaperRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_field(
        self,
        research_field_id: int,
        status: str = "queue",
        starred: bool = False,
        search: str | None = None,
    ) -> list[Paper]:
        statement = select(Paper).where(
            Paper.research_field_id == research_field_id,
            Paper.discarded_at.is_(None),
        )
        if status == "queue":
            statement = statement.where(Paper.is_archived.is_(False))
        elif status == "unread":
            statement = statement.where(Paper.is_archived.is_(False), Paper.is_read.is_(False))
        elif status == "read":
            statement = statement.where(Paper.is_archived.is_(False), Paper.is_read.is_(True))
        elif status == "archived":
            statement = statement.where(Paper.is_archived.is_(True))
        if starred:
            statement = statement.where(Paper.is_starred.is_(True))
        if search:
            pattern = f"%{search.strip()}%"
            statement = statement.where(
                or_(
                    Paper.title.ilike(pattern),
                    Paper.abstract.ilike(pattern),
                    Paper.journal_name.ilike(pattern),
                    Paper.notes.ilike(pattern),
                )
            )
        statement = statement.order_by(
            Paper.is_starred.desc(),
            Paper.priority_score.desc(),
            Paper.publication_date.desc().nullslast(),
            Paper.created_at.desc(),
        )
        return list(self.db.scalars(statement))

    def get(self, paper_id: int) -> Paper | None:
        return self.db.get(Paper, paper_id)

    def list_discarded_for_field(self, research_field_id: int) -> list[Paper]:
        statement = (
            select(Paper)
            .where(
                Paper.research_field_id == research_field_id,
                Paper.discarded_at.is_not(None),
            )
            .order_by(Paper.discarded_at.desc())
        )
        return list(self.db.scalars(statement))

    def exists(self, research_field_id: int, pubmed_id: str) -> bool:
        statement = select(Paper.id).where(Paper.research_field_id == research_field_id, Paper.pubmed_id == pubmed_id)
        return self.db.scalar(statement) is not None

    def was_deleted(self, research_field_id: int, pubmed_id: str) -> bool:
        statement = select(DeletedPaper.id).where(
            DeletedPaper.research_field_id == research_field_id,
            DeletedPaper.pubmed_id == pubmed_id,
        )
        return self.db.scalar(statement) is not None

    def create_from_article(
        self,
        research_field_id: int,
        article: PubMedArticle,
        priority: PriorityScore,
    ) -> Paper:
        paper = Paper(
            research_field_id=research_field_id,
            pubmed_id=article.pubmed_id,
            journal_name=article.journal_name,
            publication_date=article.publication_date,
            author_list=article.author_list,
            publication_types=article.publication_types,
            title=article.title,
            abstract=article.abstract,
            link=article.link,
            priority_score=priority.score,
            priority_label=priority.label,
            priority_reasons=priority.reasons,
        )
        self.db.add(paper)
        return paper

    def update(self, paper: Paper, changes: dict) -> Paper:
        for key, value in changes.items():
            setattr(paper, key, value)
        self.db.commit()
        self.db.refresh(paper)
        return paper

    def delete(self, paper: Paper) -> None:
        if not self.was_deleted(paper.research_field_id, paper.pubmed_id):
            self.db.add(
                DeletedPaper(
                    research_field_id=paper.research_field_id,
                    pubmed_id=paper.pubmed_id,
                    title=paper.title,
                    publication_date=paper.publication_date,
                )
            )
        # Keep the complete paper, annotations, and ranking metadata as an audit record.
        # Normal repository queries always exclude discarded rows.
        if paper.discarded_at is None:
            paper.discarded_at = datetime.now(timezone.utc)
        paper.is_archived = True
        self.db.commit()

    def is_from_today(self, publication_date: date | None, today: date | None = None) -> bool:
        if publication_date is None:
            return False
        today = today or date.today()
        return publication_date == today

    @staticmethod
    def is_in_date_range(publication_date: date | None, start: date, end: date) -> bool:
        return publication_date is not None and start <= publication_date <= end
