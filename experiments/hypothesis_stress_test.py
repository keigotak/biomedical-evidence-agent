"""Stress-test a biomedical claim from several research angles.

Experiment, not part of the audited MVP. For each angle (mechanism, human
evidence, animal model, clinical trial, safety, translatability) it re-runs
retrieval and the rule-based audit with an angle-focused query, so you can see
which parts of a claim rest on real evidence and which are only asserted. It
reuses the library end to end and needs no API key.

Usage:
    PYTHONPATH=src python experiments/hypothesis_stress_test.py --claim "<claim>"
"""

from __future__ import annotations

import argparse
from pathlib import Path

from biomedical_evidence_agent.audit import audit_card
from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus

# Each angle biases retrieval toward a different kind of evidence by appending
# angle cues to the claim before searching. The claim itself is unchanged as the
# audited proposition; the cues only steer which sentences surface.
ANGLES: dict[str, str] = {
    "mechanism": "mechanism pathway signaling molecular target",
    "human evidence": "patient cohort clinical human",
    "animal model": "mouse model in vivo animal",
    "clinical trial": "randomized controlled trial efficacy",
    "safety": "adverse toxicity safety risk",
    "translatability": "biomarker response predictive translation",
}


def _default_corpus() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample_corpus.jsonl"


def stress_test(claim: str, *, corpus: Path | None = None, top_k: int = 5) -> None:
    records = load_corpus(corpus or _default_corpus())
    retriever = ConceptAwareRetriever(records)

    print(f"# Hypothesis Stress Test\n\n> {claim}\n")
    for angle, cues in ANGLES.items():
        retrieved = retriever.search(f"{claim} {cues}", top_k=top_k)
        card = build_evidence_card(query=claim, retrieved=retrieved, claim=claim)
        audit = audit_card(card)
        label = card.verdict.label if card.verdict else "insufficient"
        top_flag = next(
            (f.message for f in audit.findings if f.severity == "high"),
            next((f.message for f in audit.findings), "no flags"),
        )
        supports = sum(1 for c in card.claims if c.stance == "supports")
        conflicts = sum(1 for c in card.claims if c.stance == "conflicts")
        print(
            f"## {angle}\n"
            f"- verdict: **{label}** ({supports} supporting / {conflicts} conflicting sentences)\n"
            f"- audit: {top_flag}\n"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, help="The claim to stress-test.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--corpus", type=Path, default=None)
    args = parser.parse_args()
    stress_test(args.claim, corpus=args.corpus, top_k=args.top_k)


if __name__ == "__main__":
    main()
