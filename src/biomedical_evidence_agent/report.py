from __future__ import annotations

from dataclasses import asdict

from .audit import what_would_change_my_mind
from .schemas import AuditReport, EvidenceCard, ReviewerCritique

# The Claim Audit Report is the product surface of BioClaim Auditor: it reframes
# the evidence card as an auditable artifact a researcher can review. It reuses
# the card's stance-grouped claims and verdict, and layers the rule-based audit,
# the optional reviewer critique, and a "what would change my mind" section on
# top — the things that separate an audit from a smooth answer.

_SEVERITY_MARK = {"high": "🔴", "warn": "🟡", "info": "🟢"}


def render_claim_audit(
    card: EvidenceCard,
    audit: AuditReport,
    critique: ReviewerCritique | None = None,
) -> str:
    label = card.verdict.label if card.verdict else "insufficient"
    lines = [
        "# Claim Audit Report",
        "",
        "## Claim",
        f"> {card.claim or card.query}",
        "",
        "## Audit Verdict",
    ]
    if card.verdict:
        lines.append(
            f"**{label}** (strength {card.verdict.strength:+.2f}) — {card.verdict.rationale}"
        )
    else:
        lines.append("**insufficient** — no verdict could be computed.")

    _append_evidence_map(lines, card)
    _append_claim_group(lines, "Supporting Evidence", card, "supports")
    _append_claim_group(lines, "Conflicting Evidence", card, "conflicts")
    _append_claim_group(lines, "Indirect / Insufficient Evidence", card, "insufficient")
    _append_citation_audit(lines, audit)
    _append_flags(lines, "Overclaim Flags", audit, "overclaim")
    _append_flags(lines, "Contradiction Flags", audit, "contradiction")
    _append_flags(lines, "Retrieval Gaps", audit, "retrieval-gap")

    if critique is not None:
        _append_critique(lines, critique)

    lines.extend(["", "## What Would Change My Mind?"])
    wwcmm = what_would_change_my_mind(card, audit)
    lines.extend(f"- {item}" for item in wwcmm) if wwcmm else lines.append("- Nothing identified.")

    lines.extend(["", "## Suggested Next Checks"])
    lines.extend(f"- {item}" for item in card.next_checks) if card.next_checks else lines.append(
        "- None."
    )

    lines.extend(["", "## Limitations"])
    lines.extend(f"- {item}" for item in card.limitations) if card.limitations else lines.append(
        "- None recorded."
    )
    lines.extend(
        [
            "- Research signal only — not medical advice, not a validated clinical assessment.",
        ]
    )
    return "\n".join(lines)


def _append_evidence_map(lines: list[str], card: EvidenceCard) -> None:
    lines.extend(["", "## Evidence Map"])
    counts = {"supports": 0, "conflicts": 0, "insufficient": 0}
    for claim in card.claims:
        counts[claim.stance] = counts.get(claim.stance, 0) + 1
    v = card.verdict
    lines.append(
        f"- Independent sources: {v.support_sources if v else 0} supporting, "
        f"{v.conflict_sources if v else 0} conflicting"
    )
    lines.append(
        f"- Sentences: {counts['supports']} supporting · {counts['conflicts']} "
        f"conflicting · {counts['insufficient']} indirect"
    )
    lines.append(f"- Records retrieved: {len(card.retrieved)}")


def _append_claim_group(
    lines: list[str], heading: str, card: EvidenceCard, stance: str
) -> None:
    lines.extend(["", f"## {heading}"])
    selected = [c for c in card.claims if c.stance == stance]
    if not selected:
        lines.append("- None.")
        return
    seen: dict[str, int] = {}
    for claim in selected:
        if seen.get(claim.source_id, 0) >= 2:
            continue
        seen[claim.source_id] = seen.get(claim.source_id, 0) + 1
        provenance = f"{claim.source_id}@{claim.start}-{claim.end}"
        lines.append(
            f"- [{claim.confidence} | {claim.tier} | {provenance}] {claim.text}"
        )


def _append_citation_audit(lines: list[str], audit: AuditReport) -> None:
    lines.extend(["", "## Citation Audit"])
    pct = audit.citation_faithfulness * 100
    lines.append(
        f"- {audit.citations_verbatim}/{audit.citations_checked} cited quotes are "
        f"verbatim spans of their source ({pct:.0f}% faithful)."
    )
    for flag in audit.findings:
        if flag.category == "citation":
            mark = _SEVERITY_MARK.get(flag.severity, "")
            lines.append(f"- {mark} {flag.message} {flag.detail}".rstrip())


def _append_flags(
    lines: list[str], heading: str, audit: AuditReport, category: str
) -> None:
    lines.extend(["", f"## {heading}"])
    flags = [f for f in audit.findings if f.category == category]
    if not flags:
        lines.append("- None.")
        return
    for flag in flags:
        mark = _SEVERITY_MARK.get(flag.severity, "")
        detail = f" ({flag.detail})" if flag.detail else ""
        lines.append(f"- {mark} {flag.message}{detail}")


def _append_critique(lines: list[str], critique: ReviewerCritique) -> None:
    lines.extend(["", f"## Reviewer Critique ({critique.reviewer})"])
    lines.append(f"_{critique.assessment}_")
    for finding in critique.findings:
        citation = (
            f" [{finding.source_id}: “{finding.quote}”]" if finding.quote else ""
        )
        lines.append(f"- **{finding.kind}:** {finding.note}{citation}")


def audit_json(
    card: EvidenceCard,
    audit: AuditReport,
    critique: ReviewerCritique | None = None,
) -> dict:
    """Machine-readable Claim Audit Report for programmatic downstream use."""

    return {
        "claim": card.claim or card.query,
        "source": card.source,
        "verdict": asdict(card.verdict) if card.verdict else None,
        "evidence": {
            "supporting": _claims_json(card, "supports"),
            "conflicting": _claims_json(card, "conflicts"),
            "indirect": _claims_json(card, "insufficient"),
        },
        "citation_audit": {
            "checked": audit.citations_checked,
            "verbatim": audit.citations_verbatim,
            "faithfulness": round(audit.citation_faithfulness, 3),
        },
        "flags": [asdict(f) for f in audit.findings],
        "reviewer_critique": (
            {
                "reviewer": critique.reviewer,
                "assessment": critique.assessment,
                "findings": [asdict(f) for f in critique.findings],
            }
            if critique is not None
            else None
        ),
        "what_would_change_my_mind": what_would_change_my_mind(card, audit),
        "next_checks": list(card.next_checks),
        "limitations": list(card.limitations),
    }


def _claims_json(card: EvidenceCard, stance: str) -> list[dict]:
    return [
        {
            "source_id": c.source_id,
            "text": c.text,
            "tier": c.tier,
            "confidence": c.confidence,
            "span": [c.start, c.end],
        }
        for c in card.claims
        if c.stance == stance
    ]
