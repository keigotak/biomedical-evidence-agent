from __future__ import annotations

import json
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

from .schemas import CorpusRecord

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedError(RuntimeError):
    """Raised when the optional PubMed retrieval path fails."""


def search_pubmed(query: str, top_k: int = 5) -> list[CorpusRecord]:
    """Retrieve PubMed title/abstract metadata for a research demo.

    This intentionally uses public metadata only. It does not fetch full text,
    use proprietary sources, or make clinical recommendations.
    """

    pmids = _esearch(query, top_k)
    if not pmids:
        return []
    return _efetch(pmids)


def _esearch(query: str, top_k: int) -> list[str]:
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": str(top_k),
        "sort": "relevance",
        "tool": "biomedical-evidence-agent",
    }
    payload = _get("esearch.fcgi", params)
    data = json.loads(payload)
    return data.get("esearchresult", {}).get("idlist", [])


def _efetch(pmids: list[str]) -> list[CorpusRecord]:
    params = {
        "db": "pubmed",
        "id": ",".join(pmids),
        "retmode": "xml",
        "tool": "biomedical-evidence-agent",
    }
    payload = _get("efetch.fcgi", params)
    root = ET.fromstring(payload)
    records: list[CorpusRecord] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = article.findtext(".//PMID") or "unknown"
        title = _text(article.find(".//ArticleTitle")) or "Untitled PubMed record"
        abstract_parts = [
            _text(node)
            for node in article.findall(".//Abstract/AbstractText")
            if _text(node)
        ]
        abstract = " ".join(abstract_parts) or title
        year = _year(article)
        records.append(
            CorpusRecord(
                id=f"pubmed-{pmid}",
                title=title,
                year=year,
                entities={"genes": [], "diseases": [], "drugs": []},
                abstract=abstract,
                evidence_type="public_literature",
            )
        )
    return records


def _get(endpoint: str, params: dict[str, str]) -> str:
    url = f"{NCBI_BASE}/{endpoint}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(url, headers={"User-Agent": "biomedical-evidence-agent"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8")
    except OSError as exc:
        raise PubMedError(f"PubMed request failed: {exc}") from exc


def _text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return "".join(node.itertext()).strip()


def _year(article: ET.Element) -> int:
    for path in (
        ".//ArticleDate/Year",
        ".//JournalIssue/PubDate/Year",
        ".//PubmedPubDate/Year",
    ):
        value = article.findtext(path)
        if value and value.isdigit():
            return int(value)
    return 0
