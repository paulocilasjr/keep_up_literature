from datetime import date

from app.models.research_field import ResearchField
from app.services.priority_scorer import PaperPriorityScorer
from app.services.pubmed_client import PubMedArticle


def test_priority_scorer_rewards_journal_type_keywords_and_recency() -> None:
    field = ResearchField(
        name="Cancer immunotherapy",
        keywords=["checkpoint blockade", "tumor microenvironment"],
        pubmed_query='"checkpoint blockade"[Title/Abstract]',
    )
    article = PubMedArticle(
        pubmed_id="123",
        journal_name="Nature Medicine",
        publication_date=date(2026, 5, 12),
        author_list=["Doe J"],
        publication_types=["Randomized Controlled Trial"],
        title="Checkpoint blockade reshapes the tumor microenvironment",
        abstract="A checkpoint blockade trial in the tumor microenvironment.",
        link="https://pubmed.ncbi.nlm.nih.gov/123/",
    )

    priority = PaperPriorityScorer().score(article, field, today=date(2026, 5, 15))

    assert priority.score >= 75
    assert priority.label == "Must read"
    assert any("High-impact journal" in reason for reason in priority.reasons)
    assert any("Publication type" in reason for reason in priority.reasons)
