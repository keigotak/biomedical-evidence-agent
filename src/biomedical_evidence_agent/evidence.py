from __future__ import annotations

import re

from .retrieval import tokenize
from .schemas import EvidenceCard, EvidenceClaim, RetrievedRecord

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
CONFLICT_CUES = {
    "no",
    "not",
    "without",
    "lack",
    "lacks",
    "failed",
    "fails",
    "conflicting",
    "contradictory",
    "negative",
}
INSUFFICIENT_CUES = {
    "may",
    "might",
    "could",
    "unclear",
    "requires",
    "require",
    "needed",
    "hypothesis",
    "hypotheses",
    "indirect",
}


def build_evidence_card(
    query: str,
    retrieved: list[RetrievedRecord],
    *,
    claim: str | None = None,
    source: str = "sample",
) -> EvidenceCard:
    claims = extract_claims(claim or query, retrieved)
    return EvidenceCard(
        query=query,
        retrieved=retrieved,
        claims=claims,
        claim=claim,
        source=source,
        limitations=[
            "Uses toy/sample abstracts by default; optional PubMed mode uses public metadata.",
            "Deterministic stance labeling is a scaffold for a future model-backed extractor.",
            "Evidence labels are illustrative research signals, not clinical guidance.",
        ],
        next_checks=[
            "Review cited records manually before drawing scientific conclusions.",
            "Add model-based claim extraction with citation-grounded outputs.",
            "Evaluate evidence support with a curated benchmark.",
        ],
    )


def extract_claims(query: str, retrieved: list[RetrievedRecord]) -> list[EvidenceClaim]:
    query_terms = set(tokenize(query))
    claims: list[EvidenceClaim] = []
    for item in retrieved:
        sentences = SENTENCE_RE.split(item.record.abstract)
        for sentence in sentences:
            sentence_terms = set(tokenize(sentence))
            if len(query_terms & sentence_terms) < 2:
                continue
            claims.append(
                EvidenceClaim(
                    text=sentence.strip(),
                    source_id=item.record.id,
                    evidence_type=item.record.evidence_type,
                    confidence=_confidence(item.score),
                    stance=_stance(sentence, query_terms, sentence_terms, item.score),
                )
            )
    return claims


def render_markdown(card: EvidenceCard) -> str:
    lines = [
        "# Evidence Card",
        "",
        f"Source: {card.source}",
        f"Query: {card.query}",
    ]
    if card.claim:
        lines.append(f"Claim: {card.claim}")

    lines.extend(["", "## Retrieved Evidence"])
    for item in card.retrieved:
        lines.append(
            f"- {item.record.id} ({item.record.year}) score={item.score}: {item.record.title}"
        )

    _append_claim_group(lines, "Supporting Evidence", card.claims, "supports")
    _append_claim_group(lines, "Conflicting Evidence", card.claims, "conflicts")
    _append_claim_group(lines, "Insufficient or Indirect Evidence", card.claims, "insufficient")

    lines.extend(["", "## Limitations"])
    lines.extend(f"- {item}" for item in card.limitations)
    lines.extend(["", "## Next Checks"])
    lines.extend(f"- {item}" for item in card.next_checks)
    return "\n".join(lines)


def _confidence(score: float) -> str:
    if score >= 0.45:
        return "high"
    if score >= 0.25:
        return "medium"
    return "low"


def _stance(
    sentence: str,
    query_terms: set[str],
    sentence_terms: set[str],
    score: float,
) -> str:
    overlap = len(query_terms & sentence_terms)
    if INSUFFICIENT_CUES & sentence_terms or score < 0.3:
        return "insufficient"
    if CONFLICT_CUES & sentence_terms and overlap >= 2:
        return "conflicts"
    return "supports"


def _append_claim_group(
    lines: list[str],
    heading: str,
    claims: list[EvidenceClaim],
    stance: str,
) -> None:
    lines.extend(["", f"## {heading}"])
    selected = [claim for claim in claims if claim.stance == stance]
    if not selected:
        lines.append("- No extracted evidence in this category.")
        return
    for claim in selected:
        lines.append(
            f"- [{claim.confidence} | {claim.evidence_type} | {claim.source_id}] {claim.text}"
        )
