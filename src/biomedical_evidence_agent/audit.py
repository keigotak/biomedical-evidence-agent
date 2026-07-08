from __future__ import annotations

import re

from .ontology import Ontology
from .schemas import AuditFinding, AuditReport, EvidenceCard

# Assertive language that promises more than evidence usually earns. Presence of
# any of these in a claim raises the bar the verdict must clear before the claim
# is allowed to stand un-flagged.
_OVERCLAIM_CUES = frozenset(
    {
        "cure",
        "cures",
        "cured",
        "proven",
        "proves",
        "proof",
        "definitively",
        "definitive",
        "always",
        "never",
        "guarantee",
        "guarantees",
        "guaranteed",
        "eliminates",
        "eradicates",
        "reverses",
        "prevents",
        "completely",
        "certain",
        "undeniable",
    }
)

_PRECLINICAL_TIERS = frozenset({"in_vitro", "in_silico", "preclinical"})
_WORD_RE = re.compile(r"[a-z0-9]+")


def audit_card(card: EvidenceCard, *, ontology: Ontology | None = None) -> AuditReport:
    """Run the rule-based audit over a finished evidence card.

    Checks, each traceable to evidence: citation faithfulness (quotes are
    verbatim spans of their source), overclaim (assertive claim language not
    backed by the verdict, or a well-supported verdict resting only on
    preclinical tiers), contradiction (independent sources on both sides),
    retrieval gaps (no direct or no clinical-tier evidence), and per-entity
    coverage gaps (a normalized entity named in the claim that no retrieved
    sentence addresses). The audit never invents support — it only flags where
    the card outruns its evidence.
    """

    findings: list[AuditFinding] = []
    abstracts = {item.record.id: item.record.abstract for item in card.retrieved}
    on_claim = [c for c in card.claims if c.stance in ("supports", "conflicts")]

    checked = verbatim = 0
    for claim in on_claim:
        checked += 1
        source_text = abstracts.get(claim.source_id, "")
        if claim.text.strip() and claim.text.strip() in source_text:
            verbatim += 1
        else:
            findings.append(
                AuditFinding(
                    category="citation",
                    severity="high",
                    message="Cited quote is not a verbatim span of its source.",
                    detail=f"{claim.source_id}: {claim.text[:80]!r}",
                )
            )

    findings.extend(_overclaim_findings(card, on_claim))
    findings.extend(_contradiction_findings(card))
    findings.extend(_retrieval_gap_findings(card, on_claim))
    findings.extend(_coverage_gap_findings(card, ontology))

    return AuditReport(
        findings=tuple(findings),
        citations_checked=checked,
        citations_verbatim=verbatim,
    )


def claim_concept_coverage(
    card: EvidenceCard, ontology: Ontology | None = None
) -> list[dict]:
    """Map each normalized entity in the claim to the evidence that addresses it.

    Decomposes the claim into its ontology concepts (gene / drug / disease) and,
    for each, counts how many extracted sentences mention it and with what
    stance. This exposes which parts of a claim rest on evidence and which are
    merely asserted — the entity-level view behind the Evidence Map.
    """

    ontology = ontology or Ontology.load()
    claim_text = card.claim or card.query or ""
    coverage: list[dict] = []
    for concept_id in ontology.concept_ids(claim_text):
        concept = ontology.concepts[concept_id]
        counts = {"supports": 0, "conflicts": 0, "insufficient": 0}
        sources: set[str] = set()
        for claim in card.claims:
            if concept_id in ontology.concept_ids(claim.text):
                counts[claim.stance] = counts.get(claim.stance, 0) + 1
                sources.add(claim.source_id)
        coverage.append(
            {
                "concept_id": concept_id,
                "name": concept.canonical,
                "type": concept.type,
                "supports": counts["supports"],
                "conflicts": counts["conflicts"],
                "indirect": counts["insufficient"],
                "sources": sorted(sources),
            }
        )
    return coverage


def _coverage_gap_findings(
    card: EvidenceCard, ontology: Ontology | None
) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    for entry in claim_concept_coverage(card, ontology):
        if entry["supports"] + entry["conflicts"] + entry["indirect"] == 0:
            findings.append(
                AuditFinding(
                    category="retrieval-gap",
                    severity="warn",
                    message=(
                        f"No retrieved sentence addresses '{entry['name']}', an "
                        f"entity named in the claim ({entry['type']})."
                    ),
                )
            )
    return findings


def _overclaim_findings(card: EvidenceCard, on_claim) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    text = card.claim or card.query or ""
    words = {m.group() for m in _WORD_RE.finditer(text.lower())}
    strong = words & _OVERCLAIM_CUES
    label = card.verdict.label if card.verdict else "insufficient"

    if strong and label != "well-supported":
        findings.append(
            AuditFinding(
                category="overclaim",
                severity="high",
                message=(
                    f"Claim uses assertive language ({', '.join(sorted(strong))}) "
                    f"but the evidence verdict is '{label}', not 'well-supported'."
                ),
            )
        )

    supports = [c for c in on_claim if c.stance == "supports"]
    if label == "well-supported" and supports:
        tiers = {c.tier for c in supports}
        if tiers and tiers <= _PRECLINICAL_TIERS:
            findings.append(
                AuditFinding(
                    category="overclaim",
                    severity="warn",
                    message=(
                        "Verdict is 'well-supported' but every supporting source is "
                        f"preclinical ({', '.join(sorted(tiers))}); no clinical "
                        "confirmation."
                    ),
                )
            )
    return findings


def _contradiction_findings(card: EvidenceCard) -> list[AuditFinding]:
    verdict = card.verdict
    if verdict and verdict.support_sources > 0 and verdict.conflict_sources > 0:
        return [
            AuditFinding(
                category="contradiction",
                severity="warn",
                message=(
                    f"Evidence conflicts: {verdict.support_sources} supporting vs "
                    f"{verdict.conflict_sources} conflicting independent source(s)."
                ),
            )
        ]
    return []


def _retrieval_gap_findings(card: EvidenceCard, on_claim) -> list[AuditFinding]:
    findings: list[AuditFinding] = []
    if not card.retrieved:
        findings.append(
            AuditFinding(
                category="retrieval-gap",
                severity="high",
                message="No records were retrieved for this claim.",
            )
        )
        return findings

    if not on_claim:
        findings.append(
            AuditFinding(
                category="retrieval-gap",
                severity="high",
                message=(
                    "No retrieved sentence directly supports or refutes the claim; "
                    "only indirect matches were found."
                ),
            )
        )

    if on_claim and not any(c.tier == "clinical" for c in on_claim):
        findings.append(
            AuditFinding(
                category="retrieval-gap",
                severity="warn",
                message="No clinical-tier evidence was retrieved for or against the claim.",
            )
        )
    return findings


def what_would_change_my_mind(card: EvidenceCard, audit: AuditReport) -> list[str]:
    """Concrete evidence that would move the verdict, derived from card + audit.

    A researcher-facing "so what do I go find next" list keyed to the current
    verdict and the gaps the audit surfaced — not generic advice.
    """

    label = card.verdict.label if card.verdict else "insufficient"
    items: list[str] = []
    categories = {f.category for f in audit.findings}

    if label == "insufficient":
        items.append(
            "A source naming the exact claim entities with a directional clinical "
            "outcome — the current matches are indirect or preclinical."
        )
    elif label == "contested":
        items.append(
            "An independent, well-powered study that breaks the tie, plus a "
            "mechanism explaining why the existing reports disagree."
        )
    elif label == "mixed":
        items.append("Higher-tier evidence weighted toward one direction to resolve the mix.")
    elif label == "well-supported":
        items.append(
            "A well-powered contradicting result, or evidence of publication bias, "
            "since nothing currently opposes the claim."
        )

    if any(
        f.category == "overclaim" and f.severity == "warn" for f in audit.findings
    ):
        items.append("Human/clinical confirmation — the support so far is preclinical only.")
    if "retrieval-gap" in categories:
        items.append("A broader or clinical-tier search; the current retrieval has gaps.")
    if any(f.category == "citation" for f in audit.findings):
        items.append("Re-grounding of the flagged quotes against their source text.")

    return items
