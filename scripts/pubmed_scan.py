"""Audit a batch of real biomedical claims against live PubMed; show the spread.

A "does this behave like a system, not a demo" check: run the same audit over a
spread of well-known claims — some the literature supports, some it contradicts,
some overreach. The deterministic extractor runs with no API key (network only).
If ``ANTHROPIC_API_KEY`` is set, it ALSO runs the real Claude extractor on the
same abstracts and shows both verdicts side by side — a claim-level ablation of
why messy real literature needs a model to read it.

    python scripts/pubmed_scan.py               # deterministic only (no key)
    ANTHROPIC_API_KEY=... python scripts/pubmed_scan.py   # + Claude column
"""

from __future__ import annotations

import os
from collections import Counter

from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.pubmed import PubMedError, search_pubmed
from biomedical_evidence_agent.schemas import RetrievedRecord

CLAIMS = [
    "BRAF V600E melanoma is associated with response to targeted inhibitor treatment.",
    "EGFR mutations predict response to EGFR tyrosine kinase inhibitors in non-small cell lung cancer.",
    "Trastuzumab improves survival in HER2-positive breast cancer.",
    "Aspirin reduces the risk of colorectal cancer.",
    "Vitamin D supplementation reduces the risk of cancer.",
    "Antioxidant supplements reduce all-cause mortality.",
    "Beta-carotene supplementation prevents lung cancer.",
    "Vitamin C supplementation prevents the common cold.",
    "Ivermectin reduces mortality in COVID-19.",
    "Hydroxychloroquine reduces mortality in COVID-19.",
]
_ORDER = ("well-supported", "contested", "mixed", "contradicted", "insufficient")


def _verdict(retrieved, claim, extractor):
    card = build_evidence_card(query=claim, retrieved=retrieved, claim=claim, extractor=extractor)
    return card.verdict.label if card.verdict else "insufficient"


def main(top_k: int = 6) -> None:
    llm = None
    if os.environ.get("ANTHROPIC_API_KEY"):
        from biomedical_evidence_agent.extraction import LLMClaimExtractor, anthropic_responder
        llm = LLMClaimExtractor(responder=anthropic_responder())

    det_dist: Counter = Counter()
    llm_dist: Counter = Counter()
    print("# PubMed claim scan — live PubMed\n")
    if llm:
        print("Deterministic extractor vs the real Claude extractor on the same abstracts.\n")
        print("| Claim | Deterministic | Claude |")
        print("|---|---|---|")
    else:
        print("Deterministic extractor (set ANTHROPIC_API_KEY to add a real-Claude column).\n")
        print("| Claim | Verdict |")
        print("|---|---|")

    for claim in CLAIMS:
        try:
            records = search_pubmed(claim, top_k=top_k)
        except PubMedError as exc:
            print(f"| {claim[:56]} | (pubmed error: {exc}) |" + (" — |" if llm else ""))
            continue
        retrieved = [RetrievedRecord(record=r, score=1.0 - i * 0.05) for i, r in enumerate(records)]
        det = _verdict(retrieved, claim, None)
        det_dist[det] += 1
        short = claim if len(claim) <= 56 else claim[:53] + "…"
        if llm:
            lv = _verdict(retrieved, claim, llm)
            llm_dist[lv] += 1
            print(f"| {short} | {det} | **{lv}** |")
        else:
            print(f"| {short} | **{det}** |")

    def _dist(name, d):
        print(f"\n## {name}")
        for label in _ORDER:
            if d.get(label):
                print(f"- {label}: {d[label]}")

    _dist("Deterministic distribution", det_dist)
    if llm:
        _dist("Claude distribution", llm_dist)


if __name__ == "__main__":
    main()
