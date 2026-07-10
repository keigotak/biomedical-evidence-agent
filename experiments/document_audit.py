"""Audit every claim in a passage of text, not just one you hand it.

Experiment, not part of the audited MVP. You paste a paragraph — a paper's
discussion, a review's conclusion, a press release — and this pulls out the
sentences that actually make a biological claim (they ground a gene or drug
concept *and* assert an association), audits each one through the same pipeline
the CLI uses, and prints a batch report that surfaces the overclaims and
contradictions hiding in an otherwise smooth paragraph.

Claim segmentation is deliberately conservative and offline: it reuses the
ontology backbone (a sentence only counts as a claim if it names a gene/drug
concept and carries an assertion cue), so it needs no API key and can't
hallucinate a claim the text didn't make. It will miss claims phrased without a
cue word — that's the honest tradeoff for zero false claims.

    PYTHONPATH=src python experiments/document_audit.py            # default demo passage
    PYTHONPATH=src python experiments/document_audit.py --text "BRAF ... . EGFR ... ."
    PYTHONPATH=src python experiments/document_audit.py --file discussion.txt
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from biomedical_evidence_agent.audit import audit_card
from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.ontology import Ontology
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus

# A realistic mixed paragraph over the bundled corpus: a supportable claim, a
# contested one, a flat overclaim, and an emerging association — so the batch
# report shows the full spread on offline sample data.
DEFAULT_PASSAGE = (
    "BRAF V600E melanoma is associated with response to targeted inhibitor "
    "treatment, and this has reshaped first-line care. In non-small cell lung "
    "cancer, EGFR variants are associated with response to TKI therapy. However, "
    "TP53 mutation definitively cures colorectal cancer with salbutamol. Emerging "
    "work suggests TREM2 is associated with Alzheimer's disease progression. The "
    "assay was run in triplicate at room temperature."
)

# Assertion cues that turn a concept-bearing sentence into a testable claim.
# Kept broad but bounded — a sentence with a gene/drug but none of these (a
# methods sentence, a definition) is not audited.
_ASSERTION_CUES = (
    "associat", "response", "responds", "predict", "reduc", "increas", "improv",
    "prevent", "cure", "cause", "inhibit", "block", "slow", "lower", "rais",
    "efficac", "effective", "benefit", "risk", "treat", "suppress", "progress",
)

_SEVERITY_RANK = {"high": 0, "warn": 1, "info": 2}
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")


def split_sentences(text: str) -> list[str]:
    """Split a passage into sentences (conservative; abbreviation-tolerant enough)."""

    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def extract_claims(passage: str, ontology: Ontology) -> list[str]:
    """Return the sentences that make an auditable biological claim.

    A sentence qualifies only if it grounds a gene or drug concept AND carries an
    assertion cue — the two-part gate is what keeps methods/background sentences
    (and anything the ontology doesn't recognize) out of the audit.
    """

    claims: list[str] = []
    for sentence in split_sentences(passage):
        lowered = sentence.lower()
        has_cue = any(cue in lowered for cue in _ASSERTION_CUES)
        if not has_cue:
            continue
        concept_types = {
            m.concept.type for m in ontology.normalize(sentence)
        }
        if concept_types & {"gene", "drug"}:
            claims.append(sentence)
    return claims


def _row(card, audit) -> dict:
    verdict = card.verdict
    flags = sorted(audit.findings, key=lambda f: _SEVERITY_RANK.get(f.severity, 3))
    return {
        "verdict": verdict.label if verdict else "insufficient",
        "support": verdict.support_sources if verdict else 0,
        "conflict": verdict.conflict_sources if verdict else 0,
        "top_flag": flags[0] if flags else None,
        "cites": f"{audit.citations_verbatim}/{audit.citations_checked}",
    }


def audit_document(
    passage: str,
    *,
    corpus: Path | None = None,
    ontology: Ontology | None = None,
    top_k: int = 3,
) -> dict:
    """Segment ``passage`` into claims and audit each. Returns a structured result."""

    ontology = ontology or Ontology.load()
    records = load_corpus(
        corpus or Path(__file__).resolve().parents[1] / "data" / "sample_corpus.jsonl"
    )
    retriever = ConceptAwareRetriever(records)

    claims = extract_claims(passage, ontology)
    audited = []
    for claim in claims:
        card = build_evidence_card(
            query=claim, retrieved=retriever.search(claim, top_k=top_k), claim=claim
        )
        audit = audit_card(card)
        audited.append({"claim": claim, **_row(card, audit)})
    return {"claims_found": len(claims), "audited": audited}


def render_document_audit(result: dict) -> str:
    lines = [
        "# Document Audit",
        "",
        f"Found **{result['claims_found']}** auditable claim(s) in the passage.",
        "",
        "| Claim | Verdict | Support/Conflict | Top flag | Citations |",
        "|---|---|---|---|---|",
    ]
    notable: list[str] = []
    for row in result["audited"]:
        claim = row["claim"]
        short = claim if len(claim) <= 64 else claim[:61] + "…"
        flag = row["top_flag"]
        flag_label = f"{flag.category}" if flag else "—"
        lines.append(
            f"| {short} | **{row['verdict']}** | {row['support']}/{row['conflict']} "
            f"| {flag_label} | {row['cites']} verbatim |"
        )
        if flag and flag.severity == "high":
            notable.append(f"- 🔴 **{flag.category}** — {short}")
        elif row["verdict"] in {"contested", "contradicted"}:
            notable.append(f"- 🟡 {row['verdict']} — {short}")

    lines.append("")
    lines.append("## Flags of note")
    lines.extend(notable or ["- None — every claim in the passage held up."])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--text", help="Passage to audit (quoted).")
    source.add_argument("--file", type=Path, help="Read the passage from a file.")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--corpus", type=Path, default=None)
    args = parser.parse_args()

    if args.file:
        passage = args.file.read_text(encoding="utf-8")
    elif args.text:
        passage = args.text
    else:
        passage = DEFAULT_PASSAGE

    result = audit_document(passage, corpus=args.corpus, top_k=args.top_k)
    print(render_document_audit(result))


if __name__ == "__main__":
    main()
