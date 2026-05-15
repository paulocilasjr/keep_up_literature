from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable
from xml.etree import ElementTree

import httpx


@dataclass(frozen=True)
class PubMedArticle:
    pubmed_id: str
    journal_name: str | None
    publication_date: date | None
    author_list: list[str]
    publication_types: list[str]
    title: str
    abstract: str | None
    link: str


class PubMedClient:
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(
        self,
        email: str | None = None,
        api_key: str | None = None,
        retmax: int = 50,
        timeout_seconds: float = 30.0,
    ) -> None:
        self.email = email
        self.api_key = api_key
        self.retmax = retmax
        self.timeout_seconds = timeout_seconds

    def search_current_month(self, query: str, today: date | None = None) -> list[PubMedArticle]:
        today = today or date.today()
        start = today.replace(day=1)
        dated_query = f'({query}) AND ("{start:%Y/%m/%d}"[Date - Publication] : "{today:%Y/%m/%d}"[Date - Publication])'
        ids = self._search_ids(dated_query)
        if not ids:
            return []
        return self._fetch_articles(ids)

    def _base_params(self) -> dict[str, str]:
        params: dict[str, str] = {}
        if self.email:
            params["email"] = self.email
        if self.api_key:
            params["api_key"] = self.api_key
        return params

    def _search_ids(self, query: str) -> list[str]:
        params = {
            **self._base_params(),
            "db": "pubmed",
            "term": query,
            "sort": "pub date",
            "retmax": str(self.retmax),
            "retmode": "json",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self.base_url}/esearch.fcgi", params=params)
            response.raise_for_status()
            payload = response.json()
        return payload.get("esearchresult", {}).get("idlist", [])

    def _fetch_articles(self, pubmed_ids: Iterable[str]) -> list[PubMedArticle]:
        ids = ",".join(pubmed_ids)
        params = {
            **self._base_params(),
            "db": "pubmed",
            "id": ids,
            "retmode": "xml",
        }
        with httpx.Client(timeout=self.timeout_seconds) as client:
            response = client.get(f"{self.base_url}/efetch.fcgi", params=params)
            response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        return [self._parse_article(article) for article in root.findall(".//PubmedArticle")]

    def _parse_article(self, article_node: ElementTree.Element) -> PubMedArticle:
        pmid = self._text(article_node, ".//PMID") or ""
        article = article_node.find(".//Article")
        journal_name = self._text(article_node, ".//Journal/Title")
        title = self._text(article_node, ".//ArticleTitle") or "Untitled publication"
        abstract = self._abstract(article_node)
        authors = self._authors(article_node)
        publication_types = self._publication_types(article_node)
        publication_date = self._publication_date(article_node)
        return PubMedArticle(
            pubmed_id=pmid,
            journal_name=journal_name,
            publication_date=publication_date,
            author_list=authors,
            publication_types=publication_types,
            title=" ".join(title.split()),
            abstract=abstract,
            link=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        )

    def _abstract(self, node: ElementTree.Element) -> str | None:
        pieces = []
        for abstract_node in node.findall(".//Abstract/AbstractText"):
            label = abstract_node.attrib.get("Label")
            text = " ".join("".join(abstract_node.itertext()).split())
            if not text:
                continue
            pieces.append(f"{label}: {text}" if label else text)
        return "\n\n".join(pieces) if pieces else None

    def _authors(self, node: ElementTree.Element) -> list[str]:
        authors = []
        for author in node.findall(".//AuthorList/Author"):
            collective = self._text(author, "CollectiveName")
            if collective:
                authors.append(collective)
                continue
            last_name = self._text(author, "LastName")
            initials = self._text(author, "Initials")
            if last_name and initials:
                authors.append(f"{last_name} {initials}")
            elif last_name:
                authors.append(last_name)
        return authors

    def _publication_types(self, node: ElementTree.Element) -> list[str]:
        return [
            " ".join("".join(publication_type.itertext()).split())
            for publication_type in node.findall(".//PublicationTypeList/PublicationType")
            if "".join(publication_type.itertext()).strip()
        ]

    def _publication_date(self, node: ElementTree.Element) -> date | None:
        pub_date = node.find(".//JournalIssue/PubDate")
        if pub_date is None:
            return None
        year = self._text(pub_date, "Year")
        month = self._month_number(self._text(pub_date, "Month"))
        day = self._text(pub_date, "Day")
        if not year:
            return None
        try:
            return date(int(year), month or 1, int(day or "1"))
        except ValueError:
            return None

    def _month_number(self, value: str | None) -> int | None:
        if not value:
            return None
        if value.isdigit():
            return int(value)
        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        return month_map.get(value[:3].lower())

    def _text(self, node: ElementTree.Element, selector: str) -> str | None:
        found = node.find(selector)
        if found is None or found.text is None:
            return None
        return found.text.strip()
