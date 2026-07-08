"""Audit several claims at once and compare them side by side.

Experiment, not part of the audited MVP. Runs the same claim pipeline over a list
of claims and prints one comparison table — verdict, independent supporting vs
conflicting sources, the most severe audit flag, and citation faithfulness — so a
researcher can scan a batch and see which claims hold up, which are contested,
and which overreach. Offline; no API key required.

    PYTHONPATH=src python experiments/compare_claims.py            # default demo set
    PYTHONPATH=src python experiments/compare_claims.py --claim "..." --claim "..."
"""

from __future__ import annotations

import argparse
from pathlib import Path

from biomedical_evidence_agent.audit import audit_card
from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus

# A spread across the corpus: two oncology, two other areas, one overclaim.
DEFAULT_CLAIMS = [
    "BRAF V600E melanoma is associated with response to targeted inhibitor treatment.",
    "EGFR variants are associated with response to TKI in NSCLC.",
    "IL-17A blockade may reduce fibrosis progression in systemic sclerosis.",
    "TREM2 is associated with Alzheimer's disease progression.",
    "TP53 mutation definitively cures colorectal cancer with salbutamol.",
]

_SEVERITY_RANK = {"high": 0, "warn": 1, "info": 2}


def _row(card, audit) -> dict:
    v = card.verdict
    flags = sorted(audit.findings, key=lambda f: _SEVERITY_RANK.get(f.severity, 3))
    top_flag = f"{flags[0].category}" if flags else "—"
    return {
        "verdict": v.label if v else "insufficient",
        "support": v.support_sources if v else 0,
        "conflict": v.conflict_sources if v else 0,
        "flag": top_flag,
        "cites": f"{audit.citations_verbatim}/{audit.citations_checked}",
    }


def compare(claims: list[str], *, corpus: Path | None = None, top_k: int = 5) -> str:
    records = load_corpus(
        corpus or Path(__file__).resolve().parents[1] / "data" / "sample_corpus.jsonl"
    )
    retriever = ConceptAwareRetriever(records)
    lines = [
        "# Claim Comparison",
        "",
        "| Claim | Verdict | Support/Conflict | Top flag | Citations |",
        "|---|---|---|---|---|",
    ]
    for claim in claims:
        card = build_evidence_card(
            query=claim, retrieved=retriever.search(claim, top_k=top_k), claim=claim
        )
        r = _row(card, audit_card(card))
        short = claim if len(claim) <= 60 else claim[:57] + "…"
        lines.append(
            f"| {short} | **{r['verdict']}** | {r['support']}/{r['conflict']} "
            f"| {r['flag']} | {r['cites']} verbatim |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", action="append", help="A claim (repeatable).")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--corpus", type=Path, default=None)
    args = parser.parse_args()
    claims = args.claim or DEFAULT_CLAIMS
    print(compare(claims, corpus=args.corpus, top_k=args.top_k))


if __name__ == "__main__":
    main()
