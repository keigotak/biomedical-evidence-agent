"""Reviewer duel — an advocate and a skeptic argue a claim, a judge rules.

Experiment, not part of the audited MVP. It reuses the library's evidence card
and audit, then stages a three-agent debate:

  - Advocate: marshals the strongest supporting evidence for the claim.
  - Skeptic:  marshals conflicts, overclaims, and gaps against it.
  - Judge:    weighs both cases against the tier-weighted evidence and rules.

Like the reviewer, every quote either side cites is re-checked against its source
and dropped if it is not verbatim, so neither debater can win on a fabricated
citation. Offline mock agents run without a key; the same shapes accept a
Claude-backed responder (see reviewer.anthropic_reviewer for the pattern).

Usage:
    PYTHONPATH=src python experiments/reviewer_duel.py --claim "<claim>"
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Callable

from biomedical_evidence_agent.audit import audit_card
from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus
from biomedical_evidence_agent.schemas import AuditReport, EvidenceCard

# agent(card, audit) -> {"argument": str, "points": [{"note","source_id","quote"}]}
Debater = Callable[[EvidenceCard, AuditReport], dict]
# judge(card, audit, advocate_case, skeptic_case) -> {"winner","ruling"}
Judge = Callable[[EvidenceCard, AuditReport, dict, dict], dict]


def _default_corpus() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample_corpus.jsonl"


def _ground_points(card: EvidenceCard, points: list[dict]) -> list[dict]:
    """Drop any cited quote that is not a verbatim span of its named source."""

    abstracts = {item.record.id: item.record.abstract for item in card.retrieved}
    grounded: list[dict] = []
    for point in points:
        note = (point.get("note") or "").strip()
        if not note:
            continue
        source_id = point.get("source_id", "") or ""
        quote = (point.get("quote") or "").strip()
        if quote and quote not in abstracts.get(source_id, ""):
            quote = ""
        grounded.append({"note": note, "source_id": source_id, "quote": quote})
    return grounded


def mock_advocate() -> Debater:
    def respond(card: EvidenceCard, audit: AuditReport) -> dict:
        supports = [c for c in card.claims if c.stance == "supports"]
        points = [
            {
                "note": f"Supporting {c.tier} evidence ({c.confidence} confidence).",
                "source_id": c.source_id,
                "quote": c.text,
            }
            for c in supports[:3]
        ]
        n = card.verdict.support_sources if card.verdict else 0
        if points:
            argument = (
                f"The claim stands on {n} independent supporting source(s), including "
                "clinical-tier evidence. The conflicting reports are weaker or narrower "
                "and do not overturn the positive signal."
            )
        else:
            argument = (
                "The supporting evidence is thin, but the claim remains plausible and "
                "worth pursuing pending more targeted data."
            )
        return {"argument": argument, "points": points}

    return respond


def mock_skeptic() -> Debater:
    def respond(card: EvidenceCard, audit: AuditReport) -> dict:
        conflicts = [c for c in card.claims if c.stance == "conflicts"]
        points = [
            {
                "note": f"Conflicting {c.tier} evidence ({c.confidence} confidence).",
                "source_id": c.source_id,
                "quote": c.text,
            }
            for c in conflicts[:3]
        ]
        for flag in audit.findings:
            if flag.category in ("overclaim", "retrieval-gap"):
                points.append({"note": f"[{flag.category}] {flag.message}", "source_id": "", "quote": ""})
        argument = (
            "The claim is not settled: there is conflicting evidence and/or the "
            "language outruns what the sources support. Treat it as provisional "
            "until an independent, higher-tier study resolves the disagreement."
        )
        return {"argument": argument, "points": points}

    return respond


def mock_judge() -> Judge:
    def respond(card, audit, advocate_case, skeptic_case) -> dict:
        label = card.verdict.label if card.verdict else "insufficient"
        strength = card.verdict.strength if card.verdict else 0.0
        if label == "well-supported":
            winner, lean = "advocate", "the tier-weighted balance clearly favors support"
        elif label == "insufficient":
            winner, lean = "skeptic", "no directional evidence clears the bar"
        else:  # contested / mixed
            winner, lean = "draw", "credible evidence sits on both sides"
        ruling = (
            f"Verdict '{label}' (strength {strength:+.2f}): {lean}. "
            f"Advocate raised {len(advocate_case['points'])} point(s); "
            f"skeptic raised {len(skeptic_case['points'])}. "
            "Ruling is grounded in the same tier-weighted, source-level evidence, "
            "not rhetorical force."
        )
        return {"winner": winner, "ruling": ruling}

    return respond


# --- Claude-backed debaters (optional; behind the `llm` extra) ----------------
# Same responder shapes as the mocks, so run_duel treats them identically — and
# `_ground_points` still drops any quote a model invents, so a real advocate or
# skeptic can no more fabricate a citation than the mock can.

DEFAULT_MODEL = "claude-opus-4-8"

_CASE_SCHEMA = {
    "type": "object",
    "properties": {
        "argument": {"type": "string"},
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "note": {"type": "string"},
                    "source_id": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["note", "source_id", "quote"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["argument", "points"],
    "additionalProperties": False,
}

_JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "winner": {"type": "string", "enum": ["advocate", "skeptic", "draw"]},
        "ruling": {"type": "string"},
    },
    "required": ["winner", "ruling"],
    "additionalProperties": False,
}

_ADVOCATE_SYSTEM = (
    "You are the advocate in a scientific debate. Argue that the claim is "
    "supported by the evidence. Marshal the strongest supporting sources. Quote "
    "evidence VERBATIM from the provided abstracts — never paraphrase. Be honest "
    "about the tier and strength of what you cite."
)
_SKEPTIC_SYSTEM = (
    "You are the skeptic in a scientific debate. Argue that the claim is not yet "
    "established. Marshal conflicting evidence, overclaims, and gaps. Quote "
    "evidence VERBATIM from the provided abstracts — never paraphrase."
)
_JUDGE_SYSTEM = (
    "You are the judge of a scientific debate. Weigh both cases against the "
    "tier-weighted, source-level evidence — not rhetorical force. Rule 'advocate', "
    "'skeptic', or 'draw', and explain why in two or three sentences."
)


def _anthropic_client(api_key: str | None = None):
    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise RuntimeError(
            "The Claude duel requires the optional 'llm' extra: pip install '.[llm]'"
        ) from exc
    return anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()


def _evidence_prompt(card: EvidenceCard) -> str:
    lines = [f"Claim: {card.claim or card.query}", "", "Source abstracts:"]
    for item in card.retrieved:
        lines.append(f"[{item.record.id}] {item.record.abstract}")
    return "\n".join(lines)


def _structured_call(client, system: str, prompt: str, schema: dict) -> dict:
    import json

    message = client.messages.create(
        model=DEFAULT_MODEL,
        max_tokens=16000,
        system=system,
        output_config={"format": {"type": "json_schema", "schema": schema}},
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in message.content if b.type == "text"), "")
    return json.loads(text) if text else {}


def anthropic_agents(api_key: str | None = None) -> tuple[Debater, Debater, Judge]:
    """Build Claude-backed (advocate, skeptic, judge) sharing one client."""

    client = _anthropic_client(api_key)

    def advocate(card: EvidenceCard, audit: AuditReport) -> dict:
        return _structured_call(client, _ADVOCATE_SYSTEM, _evidence_prompt(card), _CASE_SCHEMA)

    def skeptic(card: EvidenceCard, audit: AuditReport) -> dict:
        prompt = _evidence_prompt(card)
        if audit.findings:
            prompt += "\n\nRule-based audit flags:\n" + "\n".join(
                f"- [{f.category}] {f.message}" for f in audit.findings
            )
        return _structured_call(client, _SKEPTIC_SYSTEM, prompt, _CASE_SCHEMA)

    def judge(card, audit, advocate_case, skeptic_case) -> dict:
        prompt = (
            _evidence_prompt(card)
            + f"\n\nAdvocate: {advocate_case.get('argument', '')}\n"
            + "\n".join(f"- {p['note']}" for p in advocate_case.get("points", []))
            + f"\n\nSkeptic: {skeptic_case.get('argument', '')}\n"
            + "\n".join(f"- {p['note']}" for p in skeptic_case.get("points", []))
        )
        return _structured_call(client, _JUDGE_SYSTEM, prompt, _JUDGE_SCHEMA)

    return advocate, skeptic, judge


def run_duel(
    claim: str,
    *,
    corpus: Path | None = None,
    top_k: int = 5,
    advocate: Debater | None = None,
    skeptic: Debater | None = None,
    judge: Judge | None = None,
) -> dict:
    records = load_corpus(corpus or _default_corpus())
    retrieved = ConceptAwareRetriever(records).search(claim, top_k=top_k)
    card = build_evidence_card(query=claim, retrieved=retrieved, claim=claim)
    audit = audit_card(card)

    advocate = advocate or mock_advocate()
    skeptic = skeptic or mock_skeptic()
    judge = judge or mock_judge()

    advocate_case = advocate(card, audit)
    advocate_case["points"] = _ground_points(card, advocate_case.get("points", []))
    skeptic_case = skeptic(card, audit)
    skeptic_case["points"] = _ground_points(card, skeptic_case.get("points", []))
    ruling = judge(card, audit, advocate_case, skeptic_case)
    return {"card": card, "advocate": advocate_case, "skeptic": skeptic_case, "ruling": ruling}


def _print_case(title: str, case: dict) -> None:
    print(f"## {title}\n")
    print(f"{case['argument']}\n")
    for point in case["points"]:
        cite = f" [{point['source_id']}: “{point['quote']}”]" if point["quote"] else ""
        print(f"- {point['note']}{cite}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim", required=True, help="The claim to debate.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--corpus", type=Path, default=None)
    parser.add_argument(
        "--mode",
        choices=["mock", "claude"],
        default="mock",
        help="'claude' runs the debaters on the real API (needs the 'llm' extra + ANTHROPIC_API_KEY).",
    )
    args = parser.parse_args()

    agents: dict = {}
    if args.mode == "claude":
        advocate, skeptic, judge = anthropic_agents()
        agents = {"advocate": advocate, "skeptic": skeptic, "judge": judge}

    result = run_duel(args.claim, corpus=args.corpus, top_k=args.top_k, **agents)
    print(f"# Reviewer Duel\n\n> {args.claim}\n")
    _print_case("Advocate", result["advocate"])
    _print_case("Skeptic", result["skeptic"])
    ruling = result["ruling"]
    print(f"## Judge's Ruling — winner: **{ruling['winner']}**\n")
    print(ruling["ruling"])


if __name__ == "__main__":
    main()
