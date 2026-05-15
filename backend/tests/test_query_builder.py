from app.services.query_builder import PubMedQueryBuilder


def test_build_quotes_multi_word_terms() -> None:
    query = PubMedQueryBuilder.build(["single-cell RNA-seq", "CRISPR"])

    assert '"single-cell RNA-seq"[Title/Abstract]' in query
    assert "CRISPR[Title/Abstract]" in query
    assert " OR " in query
