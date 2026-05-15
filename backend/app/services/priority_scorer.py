from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.models.research_field import ResearchField
from app.services.pubmed_client import PubMedArticle


@dataclass(frozen=True)
class PriorityScore:
    score: float
    label: str
    reasons: list[str]


class PaperPriorityScorer:
    """Ranks papers using transparent signals available from PubMed metadata."""

    JOURNAL_WEIGHTS = {
        "nature": 18,
        "science": 18,
        "cell": 18,
        "new england journal of medicine": 20,
        "nejm": 20,
        "the lancet": 20,
        "jama": 18,
        "bmj": 14,
        "nature medicine": 20,
        "nature biotechnology": 18,
        "nature genetics": 18,
        "cancer cell": 18,
        "immunity": 16,
        "clinical cancer research": 14,
        "journal of clinical oncology": 18,
        "blood": 14,
        "pnas": 12,
    }

    PUBLICATION_TYPE_WEIGHTS = {
        "randomized controlled trial": 22,
        "clinical trial": 18,
        "meta-analysis": 18,
        "systematic review": 18,
        "practice guideline": 16,
        "guideline": 16,
        "review": 10,
    }

    def score(self, article: PubMedArticle, field: ResearchField, today: date | None = None) -> PriorityScore:
        today = today or date.today()
        score = 20.0
        reasons: list[str] = []

        score += self._journal_score(article.journal_name, reasons)
        score += self._publication_type_score(article.publication_types, reasons)
        score += self._keyword_score(article, field.keywords, reasons)
        score += self._recency_score(article.publication_date, today, reasons)

        if article.abstract:
            score += 4
            reasons.append("Abstract available")

        final_score = min(round(score, 1), 100.0)
        return PriorityScore(score=final_score, label=self._label(final_score), reasons=reasons[:6])

    def _journal_score(self, journal_name: str | None, reasons: list[str]) -> float:
        if not journal_name:
            return 0.0
        normalized = journal_name.lower()
        for journal, weight in self.JOURNAL_WEIGHTS.items():
            if journal in normalized:
                reasons.append(f"High-impact journal: {journal_name}")
                return float(weight)
        return 0.0

    def _publication_type_score(self, publication_types: list[str], reasons: list[str]) -> float:
        best_score = 0.0
        best_type = None
        normalized_types = [item.lower() for item in publication_types]
        for publication_type, weight in self.PUBLICATION_TYPE_WEIGHTS.items():
            if any(publication_type in item for item in normalized_types) and weight > best_score:
                best_score = float(weight)
                best_type = publication_type
        if best_type:
            reasons.append(f"Publication type: {best_type}")
        return best_score

    def _keyword_score(self, article: PubMedArticle, keywords: list[str], reasons: list[str]) -> float:
        title = article.title.lower()
        abstract = (article.abstract or "").lower()
        matched_terms = []
        score = 0.0

        for keyword in keywords:
            term = keyword.strip().strip('"').lower()
            if not term:
                continue
            term_score = 0.0
            if term in title:
                term_score += 8.0
            if term in abstract:
                term_score += 4.0
            if term_score:
                score += term_score
                matched_terms.append(keyword.strip().strip('"'))

        if matched_terms:
            reasons.append(f"Matches field terms: {', '.join(matched_terms[:3])}")
        return min(score, 30.0)

    def _recency_score(self, publication_date: date | None, today: date, reasons: list[str]) -> float:
        if publication_date is None:
            return 0.0
        age_days = (today - publication_date).days
        if age_days <= 7:
            reasons.append("Published in the last 7 days")
            return 8.0
        if age_days <= 14:
            reasons.append("Published in the last 14 days")
            return 6.0
        if publication_date.year == today.year and publication_date.month == today.month:
            reasons.append("Published this month")
            return 4.0
        return 0.0

    def _label(self, score: float) -> str:
        if score >= 75:
            return "Must read"
        if score >= 55:
            return "High"
        if score >= 35:
            return "Medium"
        return "Standard"
