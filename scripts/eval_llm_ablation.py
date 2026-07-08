"""Run the claim-extractor ablation against the REAL Claude backend.

The bundled evaluation ships this ablation on an offline mock responder. This
script runs the same three paths — deterministic, Claude-unguarded, Claude-hybrid
— plus citation faithfulness, on the real model, so the hybrid guard's effect is
measured on Claude's actual outputs rather than a stand-in.

Reads ANTHROPIC_API_KEY from the environment (never hardcode it). The model
responder is memoized, so the three paths reuse one call per (claim, source) —
~one call per retrieved record, not three.

    PYTHONPATH=src ANTHROPIC_API_KEY=... python scripts/eval_llm_ablation.py
"""

from __future__ import annotations

from biomedical_evidence_agent.evaluation import (
    default_corpus_path,
    evaluate_faithfulness,
    evaluate_stance,
    load_stance_cases,
)
from biomedical_evidence_agent.extraction import LLMClaimExtractor, anthropic_responder
from biomedical_evidence_agent.retrieval import load_corpus


def _memoized(inner):
    cache: dict = {}
    calls = {"n": 0}

    def respond(claim, record):
        key = (claim, record.id)
        if key not in cache:
            calls["n"] += 1
            cache[key] = inner(claim, record)
        return cache[key]

    return respond, calls


def main() -> None:
    records = load_corpus(default_corpus_path())
    cases = load_stance_cases()
    responder, calls = _memoized(anthropic_responder())

    det = evaluate_stance(records, cases)
    ung = evaluate_stance(
        records, cases, extractor=LLMClaimExtractor(responder=responder, guard=False)
    )
    hyb = evaluate_stance(
        records, cases, extractor=LLMClaimExtractor(responder=responder, guard=True)
    )
    faith = evaluate_faithfulness(records, responder, cases)

    print("# Claim Extractor Ablation — real Claude (`claude-opus-4-8`)")
    print()
    print("Same stance benchmark as the offline ablation, but the LLM paths use the")
    print("real model. The hybrid guard re-applies entity-grounding + outcome-polarity")
    print("on top of Claude's stance; faithfulness is the fraction of the model's")
    print("proposed quotes that are verbatim in the source (guard-independent).")
    print()
    print("| Path | stance macro-F1 | guardrail leaks | citation faithfulness |")
    print("|---|---|---|---|")
    print(f"| deterministic | {det.macro_f1:.3f} | {det.guardrail_violations}/{det.guardrail_items} | — |")
    print(
        f"| Claude, no guard | {ung.macro_f1:.3f} | "
        f"{ung.guardrail_violations}/{ung.guardrail_items} | {faith['rate']:.3f} "
        f"({faith['faithful']}/{faith['proposed']}) |"
    )
    print(
        f"| Claude, hybrid guard | {hyb.macro_f1:.3f} | "
        f"{hyb.guardrail_violations}/{hyb.guardrail_items} | {faith['rate']:.3f} "
        f"({faith['faithful']}/{faith['proposed']}) |"
    )
    print()
    print(f"_{calls['n']} unique model calls (memoized across the three paths)._")


if __name__ == "__main__":
    main()
