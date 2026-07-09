from __future__ import annotations

import json
import os
from typing import Callable

from .schemas import AuditReport, EvidenceCard, ReviewerCritique, ReviewFinding

# The reviewer agent reads a finished evidence card and critiques it: is the
# claim stronger than the evidence, are the citations weak, is the search for
# counter-evidence thin, and what should be pulled next. It mirrors the extractor
# design — a `reviewer` responder is injected, so a real Anthropic backend and an
# offline mock share one grounding pipeline. Any quote the reviewer cites is
# re-checked against the source, so the critique cannot smuggle in a fabricated
# citation any more than the extractor can.

DEFAULT_MODEL = "claude-opus-4-8"
REVIEW_KINDS = ("overclaim", "weak-citation", "missing-counter-evidence", "next-source")

# reviewer(card, audit) -> {"assessment": str, "findings": [{kind, note, source_id, quote}]}
Reviewer = Callable[[EvidenceCard, AuditReport], dict]

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "assessment": {"type": "string"},
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string", "enum": list(REVIEW_KINDS)},
                    "note": {"type": "string"},
                    "source_id": {"type": "string"},
                    "quote": {"type": "string"},
                },
                "required": ["kind", "note"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["assessment", "findings"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = (
    "You are a skeptical scientific reviewer auditing an evidence card for a "
    "biomedical claim. Push back where the card overreaches: flag claims stated "
    "more strongly than the evidence supports, citations that are weak or "
    "indirect, and missing searches for counter-evidence. Suggest the single most "
    "useful next source to pull. If you quote evidence, quote it VERBATIM from the "
    "provided abstracts — never paraphrase. Be concise and specific."
)


class ReviewerUnavailable(RuntimeError):
    """Raised when the model-backed reviewer cannot be constructed."""


def review_card(
    card: EvidenceCard, audit: AuditReport, *, reviewer: Reviewer
) -> ReviewerCritique:
    """Turn a reviewer responder's raw output into a grounded critique.

    Every cited quote is verified to be a verbatim span of the named source; a
    quote that is not is dropped (the note is kept) so a hallucinated citation
    can never appear in the critique.
    """

    abstracts = {item.record.id: item.record.abstract for item in card.retrieved}
    raw = reviewer(card, audit) or {}
    findings: list[ReviewFinding] = []
    for item in raw.get("findings", []):
        kind = item.get("kind", "next-source")
        note = (item.get("note") or "").strip()
        if not note:
            continue
        source_id = item.get("source_id", "") or ""
        quote = (item.get("quote") or "").strip()
        if quote and quote not in abstracts.get(source_id, ""):
            quote = ""  # drop an unfaithful citation, keep the note
        findings.append(
            ReviewFinding(kind=kind, note=note, source_id=source_id, quote=quote)
        )
    assessment = (raw.get("assessment") or "").strip() or "No assessment returned."
    reviewer_name = raw.get("reviewer", "mock")
    return ReviewerCritique(
        assessment=assessment, findings=tuple(findings), reviewer=reviewer_name
    )


def mock_reviewer() -> Reviewer:
    """Offline reviewer: a deterministic critique derived from the audit + verdict.

    It is NOT a substitute for a model's judgment — it exists so the whole
    reviewer path (card in, grounded critique out) runs without an API key, and
    so the report has a critique section in the default demo.
    """

    def respond(card: EvidenceCard, audit: AuditReport) -> dict:
        label = card.verdict.label if card.verdict else "insufficient"
        findings: list[dict] = []

        for flag in audit.findings:
            if flag.category == "overclaim":
                findings.append(
                    {
                        "kind": "overclaim",
                        "note": (
                            "The claim is stated more strongly than the evidence "
                            f"supports (verdict: {label}). " + flag.message
                        ),
                    }
                )
            elif flag.category == "contradiction":
                findings.append(
                    {
                        "kind": "missing-counter-evidence",
                        "note": (
                            "Sources disagree; do not treat this as settled. "
                            "Search specifically for the weaker side before concluding."
                        ),
                    }
                )
            elif flag.category == "retrieval-gap":
                findings.append(
                    {
                        "kind": "missing-counter-evidence",
                        "note": (
                            "Counter-evidence search looks thin. " + flag.message
                        ),
                    }
                )
            elif flag.category == "citation":
                findings.append(
                    {
                        "kind": "weak-citation",
                        "note": "A cited quote is not verbatim in its source. " + flag.message,
                    }
                )

        if audit.citations_checked and audit.citation_faithfulness == 1.0:
            findings.append(
                {
                    "kind": "weak-citation",
                    "note": (
                        f"All {audit.citations_checked} citations are verbatim, but "
                        "they are single sentences — check they are not quoted out of "
                        "context."
                    ),
                }
            )

        first = card.retrieved[0].record.id if card.retrieved else "the corpus"
        findings.append(
            {
                "kind": "next-source",
                "note": (
                    "Pull an independent, higher-tier source that names the exact "
                    f"claim entities; start beyond {first}."
                ),
            }
        )

        assessment = (
            f"Verdict '{label}' with {len(audit.findings)} audit flag(s); "
            "treat the claim as provisional pending the checks below."
        )
        return {"assessment": assessment, "findings": findings, "reviewer": "mock"}

    return respond


def anthropic_reviewer(*, model: str = DEFAULT_MODEL, api_key: str | None = None) -> Reviewer:
    """Model-backed reviewer: one structured-output critique per card.

    Behind the optional ``llm`` extra. Mirrors ``extraction.anthropic_responder``:
    raises ReviewerUnavailable (not a deep ImportError/auth error) when the SDK or
    credentials are missing, so the default offline path stays dependency-free.
    """

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ReviewerUnavailable(
            "The Claude reviewer requires the optional 'llm' extra. "
            "Install it with: pip install '.[llm]'"
        ) from exc
    # The SDK constructs happily without a key and only fails at call time, which
    # would surface as a raw traceback in the UI. Check up front so a missing key
    # degrades to a clean warning instead (mirrors extraction.anthropic_responder).
    if not (api_key or os.environ.get("ANTHROPIC_API_KEY")):
        raise ReviewerUnavailable(
            "The Claude reviewer needs ANTHROPIC_API_KEY set (or pass api_key)."
        )
    try:
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    except Exception as exc:  # pragma: no cover - depends on credential config
        raise ReviewerUnavailable(
            f"Anthropic client unavailable (set ANTHROPIC_API_KEY): {exc}"
        ) from exc

    def respond(card: EvidenceCard, audit: AuditReport) -> dict:
        prompt = _render_review_prompt(card, audit)
        try:
            message = client.messages.create(
                model=model,
                max_tokens=16000,
                system=_SYSTEM_PROMPT,
                output_config={"format": {"type": "json_schema", "schema": REVIEW_SCHEMA}},
                messages=[{"role": "user", "content": prompt}],
            )
        except anthropic.APIError as exc:  # auth/rate/connection — degrade, don't crash
            raise ReviewerUnavailable(f"Claude reviewer call failed: {exc}") from exc
        text = next((block.text for block in message.content if block.type == "text"), "")
        data = json.loads(text) if text else {}
        data["reviewer"] = "claude"
        return data

    return respond


def _render_review_prompt(card: EvidenceCard, audit: AuditReport) -> str:
    label = card.verdict.label if card.verdict else "insufficient"
    lines = [
        f"Claim: {card.claim or card.query}",
        f"Verdict: {label}"
        + (f" ({card.verdict.rationale})" if card.verdict else ""),
        "",
        "Evidence sentences (verbatim from sources):",
    ]
    for claim in card.claims:
        if claim.stance in ("supports", "conflicts"):
            lines.append(f"- [{claim.stance} | {claim.source_id}] {claim.text}")
    lines.append("")
    lines.append("Rule-based audit flags already raised:")
    if audit.findings:
        lines.extend(f"- [{f.category}] {f.message}" for f in audit.findings)
    else:
        lines.append("- none")
    lines.append("")
    lines.append("Source abstracts:")
    for item in card.retrieved:
        lines.append(f"[{item.record.id}] {item.record.abstract}")
    return "\n".join(lines)
