from __future__ import annotations

import re

from .retrieval import tokenize
from .schemas import EvidenceCard, EvidenceClaim, RetrievedRecord

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")


def build_evidence_card(query: str, retrieved: list[RetrievedRecord]) -> EvidenceCard:
    claims = extract_claims(query, retrieved)
    return EvidenceCard(
        query=query,
        retrieved=retrieved,
        claims=claims,
        limitations=[
            "Uses toy/sample abstracts only.",
            "Deterministic extraction is a scaffold for a future model-backed extractor.",
            "Evidence labels are illustrative and not clinical guidance.",
        ],
        next_checks=[
            "Validate claims against real biomedical databases.",
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
                )
            )
    return claims


def render_markdown(card: EvidenceCard) -> str:
    lines = [
        "# Evidence Card",
        "",
        f"Query: {card.query}",
        "",
        "## Retrieved Evidence",
    ]
    for item in card.retrieved:
        lines.append(
            f"- {item.record.id} ({item.record.year}) score={item.score}: {item.record.title}"
        )

    lines.extend(["", "## Extracted Claims"])
    if card.claims:
        for claim in card.claims:
            lines.append(
                f"- [{claim.confidence} | {claim.evidence_type} | {claim.source_id}] {claim.text}"
            )
    else:
        lines.append("- No claim-like sentence met the deterministic extraction threshold.")

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
