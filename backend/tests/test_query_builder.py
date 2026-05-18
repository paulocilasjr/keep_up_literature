from app.services.query_builder import PubMedQueryBuilder


def test_build_quotes_multi_word_terms() -> None:
    query = PubMedQueryBuilder.build(["single-cell RNA-seq", "CRISPR"])

    assert '"single-cell RNA-seq"[Title/Abstract]' in query
    assert "CRISPR[Title/Abstract]" in query
    assert " OR " in query


def test_build_anchors_broad_single_terms_to_specific_terms() -> None:
    query = PubMedQueryBuilder.build(["machine learning", "cancer", "deep learning"])

    assert query == (
        '("machine learning"[Title/Abstract] OR "deep learning"[Title/Abstract]) '
        "AND (cancer[Title/Abstract])"
    )


def test_build_adds_ai_context_and_pharmacology_exclusions_for_agentic_topics() -> None:
    query = PubMedQueryBuilder.build(
        ["Agentic", "biomedical Agents", "LLM agents", "cancer agents"],
        name="Agents for biomedical research",
    )

    assert "LLM[Title/Abstract]" in query
    assert '"artificial intelligence"[Title/Abstract]' in query
    assert "NOT" in query
    assert "antibiotic*[Title/Abstract]" in query
    assert '"therapeutic agents"[Title/Abstract]' in query


def test_build_keeps_single_broad_term_when_it_is_the_only_context() -> None:
    query = PubMedQueryBuilder.build(["cancer"])

    assert query == "cancer[Title/Abstract]"
