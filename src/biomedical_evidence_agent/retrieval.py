from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path

from .aliases import alias_tags
from .schemas import CorpusRecord, RetrievedRecord

TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?")


def tokenize(text: str) -> list[str]:
    return [token.lower() for token in TOKEN_RE.findall(text)]


def analyze(text: str) -> list[str]:
    """Tokenize ``text`` and append canonical alias tags for abbreviations."""

    return tokenize(text) + alias_tags(text)


def load_corpus(path: Path) -> list[CorpusRecord]:
    records: list[CorpusRecord] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            records.append(
                CorpusRecord(
                    id=item["id"],
                    title=item["title"],
                    year=int(item["year"]),
                    entities=item["entities"],
                    abstract=item["abstract"],
                    evidence_type=item["evidence_type"],
                )
            )
    return records


class LexicalRetriever:
    def __init__(self, records: list[CorpusRecord]):
        self.records = records
        self._doc_tokens = [analyze(self._record_text(record)) for record in records]
        self._idf = self._build_idf(self._doc_tokens)

    def search(self, query: str, top_k: int = 3) -> list[RetrievedRecord]:
        query_weights = self._weights(analyze(query))
        ranked: list[RetrievedRecord] = []
        for record, tokens in zip(self.records, self._doc_tokens):
            score = self._cosine(query_weights, self._weights(tokens))
            if score > 0:
                ranked.append(RetrievedRecord(record=record, score=round(score, 4)))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    def _weights(self, tokens: list[str]) -> dict[str, float]:
        counts = Counter(tokens)
        return {token: count * self._idf.get(token, 0.0) for token, count in counts.items()}

    @staticmethod
    def _record_text(record: CorpusRecord) -> str:
        entity_text = " ".join(value for values in record.entities.values() for value in values)
        return f"{record.title} {entity_text} {record.abstract}"

    @staticmethod
    def _build_idf(doc_tokens: list[list[str]]) -> dict[str, float]:
        doc_count = len(doc_tokens)
        document_frequency: Counter[str] = Counter()
        for tokens in doc_tokens:
            document_frequency.update(set(tokens))
        return {
            token: math.log((1 + doc_count) / (1 + frequency)) + 1.0
            for token, frequency in document_frequency.items()
        }

    @staticmethod
    def _cosine(left: dict[str, float], right: dict[str, float]) -> float:
        shared = set(left) & set(right)
        numerator = sum(left[token] * right[token] for token in shared)
        left_norm = math.sqrt(sum(value * value for value in left.values()))
        right_norm = math.sqrt(sum(value * value for value in right.values()))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
