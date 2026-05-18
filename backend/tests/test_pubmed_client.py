from datetime import date
from xml.etree import ElementTree

from app.services.pubmed_client import PubMedClient


def test_parse_article_prefers_electronic_article_date_over_future_issue_date() -> None:
    article = ElementTree.fromstring(
        """
        <PubmedArticle>
          <MedlineCitation>
            <PMID>42141998</PMID>
            <Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <Year>2026</Year>
                    <Month>Dec</Month>
                    <Day>31</Day>
                  </PubDate>
                </JournalIssue>
                <Title>Example Journal</Title>
              </Journal>
              <ArticleTitle>Ahead of print cancer AI paper.</ArticleTitle>
              <ArticleDate DateType="Electronic">
                <Year>2026</Year>
                <Month>05</Month>
                <Day>16</Day>
              </ArticleDate>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
    )

    parsed = PubMedClient()._parse_article(article)

    assert parsed.publication_date == date(2026, 5, 16)


def test_parse_article_falls_back_to_journal_issue_date() -> None:
    article = ElementTree.fromstring(
        """
        <PubmedArticle>
          <MedlineCitation>
            <PMID>123</PMID>
            <Article>
              <Journal>
                <JournalIssue>
                  <PubDate>
                    <Year>2026</Year>
                    <Month>May</Month>
                    <Day>03</Day>
                  </PubDate>
                </JournalIssue>
                <Title>Example Journal</Title>
              </Journal>
              <ArticleTitle>Current issue paper.</ArticleTitle>
            </Article>
          </MedlineCitation>
        </PubmedArticle>
        """
    )

    parsed = PubMedClient()._parse_article(article)

    assert parsed.publication_date == date(2026, 5, 3)
