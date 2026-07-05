from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class CorpusRecord:
    id: str
    title: str
    year: int
    entities: dict[str, list[str]]
    abstract: str
    evidence_type: str


@dataclass(frozen=True)
class RetrievedRecord:
    record: CorpusRecord
    score: float


@dataclass(frozen=True)
class EvidenceClaim:
    text: str
    source_id: str
    evidence_type: str
    confidence: str
    stance: str = "insufficient"
    facets: tuple[str, ...] = ()
    start: int = 0
    end: int = 0


@dataclass(frozen=True)
class EvidenceCard:
    query: str
    retrieved: list[RetrievedRecord]
    claims: list[EvidenceClaim]
    claim: str | None = None
    source: str = "sample"
    limitations: list[str] = field(default_factory=list)
    next_checks: list[str] = field(default_factory=list)
