import re


class PubMedQueryBuilder:
    """Builds focused PubMed Title/Abstract queries from user-provided contexts."""

    BROAD_SINGLE_TERMS = {
        "agent",
        "agents",
        "biomedical",
        "biology",
        "cancer",
        "cell",
        "cells",
        "clinical",
        "disease",
        "diseases",
        "medicine",
        "patient",
        "patients",
        "research",
        "therapy",
        "treatment",
        "trial",
        "trials",
        "tumor",
        "tumors",
    }
    AGENT_TERMS = {"agent", "agents", "agentic", "multi-agent", "multiagent"}
    AI_CONTEXT_PATTERNS = (
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
    AI_CONTEXT_CLAUSES = (
        "agentic[Title/Abstract]",
        '"artificial intelligence"[Title/Abstract]',
        "benchmark*[Title/Abstract]",
        "chatbot*[Title/Abstract]",
        '"deep learning"[Title/Abstract]',
        '"foundation model"[Title/Abstract]',
        '"large language model"[Title/Abstract]',
        "LLM[Title/Abstract]",
        '"machine learning"[Title/Abstract]',
        '"multi-agent"[Title/Abstract]',
        "multiagent[Title/Abstract]",
    )
    BIOMEDICAL_CONTEXT_CLAUSES = (
        "biomedical[Title/Abstract]",
        "cancer[Title/Abstract]",
        "clinical[Title/Abstract]",
        "disease[Title/Abstract]",
        "health[Title/Abstract]",
        "healthcare[Title/Abstract]",
        "medical[Title/Abstract]",
        "medicine[Title/Abstract]",
        "oncology[Title/Abstract]",
        "patient[Title/Abstract]",
    )
    PHARMACOLOGIC_AGENT_EXCLUSIONS = (
        '"anti-bacterial agents"[MeSH Terms]',
        '"anti-infective agents"[Title/Abstract]',
        '"antimicrobial agents"[Title/Abstract]',
        '"antineoplastic agents"[Title/Abstract]',
        '"chemotherapeutic agents"[Title/Abstract]',
        '"therapeutic agents"[Title/Abstract]',
        "antibacterial*[Title/Abstract]",
        "antibiotic*[Title/Abstract]",
        "antimicrobial*[Title/Abstract]",
        "pharmacologic*[Title/Abstract]",
        "pharmaceutical*[Title/Abstract]",
    )

    @classmethod
    def build(cls, keywords: list[str], name: str | None = None, description: str | None = None) -> str:
        cleaned = cls._clean_terms(keywords)
        broad_singletons = []
        focus_clauses = []

        for keyword in cleaned:
            if cls._is_broad_singleton(keyword) and len(cleaned) > 1:
                broad_singletons.append(cls._title_abstract_clause(keyword))
                continue
            focus_clauses.append(cls._title_abstract_clause(keyword))

        if not focus_clauses:
            focus_clauses = [cls._title_abstract_clause(keyword) for keyword in cleaned]

        query = cls._join_or(focus_clauses)
        if broad_singletons:
            query = f"({query}) AND ({cls._join_or(broad_singletons)})"

        context = " ".join([name or "", description or "", *cleaned]).lower()
        if cls._has_ai_agent_context(context):
            agent_clauses = cls._agent_clauses(cleaned)
            query = (
                f"({cls._join_or(agent_clauses)}) "
                f"AND ({cls._join_or(cls.AI_CONTEXT_CLAUSES)}) "
                f"AND ({cls._join_or(cls.BIOMEDICAL_CONTEXT_CLAUSES)})"
            )
            query = f"({query}) NOT ({cls._join_or(cls.PHARMACOLOGIC_AGENT_EXCLUSIONS)})"

        return query

    @classmethod
    def _clean_terms(cls, keywords: list[str]) -> list[str]:
        seen = set()
        cleaned = []
        for keyword in keywords:
            normalized = " ".join(keyword.strip().split())
            key = normalized.lower()
            if not normalized or key in seen:
                continue
            seen.add(key)
            cleaned.append(normalized)
        return cleaned

    @classmethod
    def _is_broad_singleton(cls, keyword: str) -> bool:
        return " " not in keyword.strip() and keyword.lower() in cls.BROAD_SINGLE_TERMS

    @classmethod
    def _has_ai_agent_context(cls, context: str) -> bool:
        has_agent_term = any(re.search(rf"\b{re.escape(term)}s?\b", context) for term in cls.AGENT_TERMS)
        has_ai_context = any(pattern in context for pattern in cls.AI_CONTEXT_PATTERNS)
        return has_agent_term and has_ai_context

    @classmethod
    def _title_abstract_clause(cls, keyword: str) -> str:
        normalized = keyword.strip()
        if " " in normalized and not (normalized.startswith('"') and normalized.endswith('"')):
            normalized = f'"{normalized}"'
        return f"{normalized}[Title/Abstract]"

    @classmethod
    def _agent_clauses(cls, keywords: list[str]) -> list[str]:
        clauses = []
        for keyword in keywords:
            if any(re.search(rf"\b{re.escape(term)}s?\b", keyword.lower()) for term in cls.AGENT_TERMS):
                clauses.append(cls._title_abstract_clause(keyword))
        clauses.append("agent*[Title/Abstract]")
        return list(dict.fromkeys(clauses))

    @staticmethod
    def _join_or(clauses: list[str] | tuple[str, ...]) -> str:
        return " OR ".join(clauses)
