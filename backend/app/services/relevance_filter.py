import re

from app.models.research_field import ResearchField
from app.services.pubmed_client import PubMedArticle
from app.services.query_builder import PubMedQueryBuilder


class LiteratureRelevanceFilter:
    """Rejects broad PubMed matches that satisfy query terms in unrelated contexts."""

    AI_PATTERNS = (
        "agentic",
        "artificial intelligence",
        "benchmark",
        "chatbot",
        "deep learning",
        "foundation model",
        "large language model",
        "llm",
        "machine learning",
        "multi-agent",
        "multiagent",
    )
    BIOMEDICAL_PATTERNS = (
        "biomedical",
        "cancer",
        "clinical",
        "disease",
        "health",
        "healthcare",
        "medical",
        "medicine",
        "oncology",
        "patient",
    )
    SOFTWARE_AGENT_PATTERNS = (
        r"\bagentic\b",
        r"\bmulti[- ]agent\b",
        r"\bchatbots?\b",
        r"\bagents?\s+(approach|architecture|automation|benchmark|framework|model|orchestrat\w*|reasoning|system|tool|workflow)\b",
        r"\b(collaborative|conversational|guideline[- ]centric|medical|reasoning|software|virtual)\s+agents?\b",
        r"\b(llm|large language model|language model)\s+agents?\b",
        r"\bagents?\s+(controlled|powered|using|with|under)\s+(llm|large language model|language model)\b",
    )
    PHARMACOLOGIC_PATTERNS = (
        "anti-bacterial agent",
        "anti-infective agent",
        "antibacterial",
        "antibiotic",
        "antimicrobial",
        "antineoplastic agent",
        "chemotherapeutic agent",
        "pharmaceutical",
        "pharmacologic",
        "therapeutic agent",
    )

    def is_relevant(self, article: PubMedArticle, field: ResearchField) -> bool:
        text = self._article_text(article)
        keywords = PubMedQueryBuilder._clean_terms(field.keywords)
        context = " ".join([field.name or "", field.description or "", *keywords]).lower()

        if PubMedQueryBuilder._has_ai_agent_context(context):
            return self._matches_ai_agent_topic(text)

        broad_singletons = [keyword for keyword in keywords if PubMedQueryBuilder._is_broad_singleton(keyword)]
        focus_terms = [keyword for keyword in keywords if not PubMedQueryBuilder._is_broad_singleton(keyword)]
        if broad_singletons and focus_terms:
            return self._matches_any(text, focus_terms) and self._matches_any(text, broad_singletons)

        return self._matches_any(text, keywords)

    def _matches_ai_agent_topic(self, text: str) -> bool:
        has_software_agent = any(re.search(pattern, text) for pattern in self.SOFTWARE_AGENT_PATTERNS)
        has_ai_context = any(pattern in text for pattern in self.AI_PATTERNS)
        has_biomedical_context = any(pattern in text for pattern in self.BIOMEDICAL_PATTERNS)
        has_pharmacologic_context = any(pattern in text for pattern in self.PHARMACOLOGIC_PATTERNS)
        return has_software_agent and has_ai_context and has_biomedical_context and not has_pharmacologic_context

    def _matches_any(self, text: str, terms: list[str]) -> bool:
        return any(self._term_in_text(text, term) for term in terms)

    def _term_in_text(self, text: str, term: str) -> bool:
        normalized = term.strip().strip('"').lower()
        if not normalized:
            return False
        return re.search(rf"\b{re.escape(normalized)}\b", text) is not None

    def _article_text(self, article: PubMedArticle) -> str:
        return f"{article.title or ''} {article.abstract or ''}".lower()
