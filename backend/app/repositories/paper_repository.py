from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.deleted_paper import DeletedPaper
from app.models.paper import Paper
from app.services.priority_scorer import PriorityScore
from app.services.pubmed_client import PubMedArticle


class PaperRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_field(self, research_field_id: int) -> list[Paper]:
        statement = (
            select(Paper)
            .where(Paper.research_field_id == research_field_id)
            .order_by(Paper.priority_score.desc(), Paper.publication_date.desc().nullslast(), Paper.created_at.desc())
        )
        return list(self.db.scalars(statement))

    def get(self, paper_id: int) -> Paper | None:
        return self.db.get(Paper, paper_id)

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

    def set_read_status(self, paper: Paper, is_read: bool) -> Paper:
        paper.is_read = is_read
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
        self.db.delete(paper)
        self.db.commit()

    def is_from_today(self, publication_date: date | None, today: date | None = None) -> bool:
        if publication_date is None:
            return False
        today = today or date.today()
        return publication_date == today
