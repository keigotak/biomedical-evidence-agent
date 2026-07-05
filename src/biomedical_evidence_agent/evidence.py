from __future__ import annotations

import re
from collections import Counter

from .aliases import alias_tags
from .ontology import Ontology
from .quant import extract_measurements
from .retrieval import tokenize
from .schemas import (
    CorpusRecord,
    EvidenceCard,
    EvidenceClaim,
    QuantMeasurement,
    RetrievedRecord,
    Verdict,
)

# A claim needs at least this much tier-weighted, on-claim evidence before a
# directional verdict is warranted; below it the verdict is "insufficient". The
# floor is one in-vitro source (weight 0.5), so a single weak sentence never
# reads as a settled result.
MIN_VERDICT_EVIDENCE = 0.5
# When both sides carry at least this share of the total weight, the claim is
# "contested" rather than leaning one way.
CONTESTED_SHARE = 0.35
# Net balance at or above this counts as well-supported (little countervailing
# evidence); between 0 and this is "mixed".
WELL_SUPPORTED_BALANCE = 0.5

GENE_TOKEN_RE = re.compile(r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)?")

# Evidence-tier strength weights. Study design is the primary determinant of how
# much a sentence should move confidence: a clinical cohort outweighs an in vitro
# assay, which outweighs an in silico prediction. Weights are centered on 0.5 so
# a tier can push confidence up or down relative to a neutral baseline.
TIER_WEIGHT: dict[str, float] = {
    "clinical": 1.0,
    "in_vivo": 0.7,
    "association": 0.6,
    "in_vitro": 0.5,
    "in_silico": 0.4,
    "unspecified": 0.5,
}
_TIER_CUES: list[tuple[str, tuple[str, ...]]] = [
    ("clinical", ("randomized", "clinical trial", "patients", "cohort")),
    ("in_vivo", ("in vivo", "mouse", "murine", "xenograft")),
    ("in_vitro", ("in vitro", "cell line", "cells", "assay")),
    ("in_silico", ("prediction", "computational", "in silico", "workflow", "single-cell")),
]

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")
CONFLICT_CUES = {
    "no",
    "not",
    "without",
    "lack",
    "lacks",
    "failed",
    "fails",
    "conflicting",
    "contradictory",
    "negative",
}
INSUFFICIENT_CUES = {
    "may",
    "might",
    "could",
    "unclear",
    "requires",
    "require",
    "needed",
    "hypothesis",
    "hypotheses",
    "indirect",
}
RESPONSE_CUES = {
    "benefit",
    "benefits",
    "durable",
    "efficacy",
    "remission",
    "response",
    "responses",
    "responsive",
    "sensitive",
    "sensitivity",
    "survival",
}
RESISTANCE_CUES = {
    "progression",
    "recurrence",
    "refractory",
    "relapse",
    "resistance",
    "resistant",
}
METHOD_TERMS = {
    "antigen",
    "binding",
    "candidate",
    "candidates",
    "expression",
    "hla",
    "neoantigen",
    "peptide",
    "prediction",
    "rna",
    "score",
    "scores",
    "variant",
    "variants",
    "workflow",
}
PREDICATE_TERMS = {
    "associated",
    "benefit",
    "benefits",
    "correlate",
    "correlates",
    "durable",
    "efficacy",
    "predict",
    "predicts",
    "prioritize",
    "combines",
    "produce",
    "produces",
    "ranking",
    "response",
    "responses",
    "resistance",
    "sensitivity",
    "survival",
}
MECHANISM_FACET = {
    "activating",
    "activation",
    "antigen",
    "binding",
    "expression",
    "kinase",
    "mutation",
    "mutations",
    "neoantigen",
    "pathway",
    "peptide",
    "presentation",
    "reactivation",
    "signaling",
    "somatic",
    "variant",
    "variants",
}
CLINICAL_FACET = {
    "benefit",
    "benefits",
    "cohort",
    "efficacy",
    "patients",
    "progression",
    "prognosis",
    "recurrence",
    "refractory",
    "relapse",
    "remission",
    "resistance",
    "resistant",
    "response",
    "responses",
    "sensitivity",
    "survival",
    "tumor",
    "tumors",
}
BIOMARKER_FACET = {
    "associated",
    "biomarker",
    "correlate",
    "correlates",
    "marker",
    "predict",
    "predicts",
    "status",
    "stratify",
}
METHOD_FACET = {
    "annotations",
    "calls",
    "prediction",
    "ranking",
    "score",
    "scores",
    "scoring",
    "sequencing",
    "typing",
    "validation",
    "workflow",
}
FACETS: dict[str, set[str]] = {
    "mechanism": MECHANISM_FACET,
    "clinical": CLINICAL_FACET,
    "biomarker": BIOMARKER_FACET,
    "method": METHOD_FACET,
}
MAX_SENTENCES_PER_SOURCE_STANCE = 2


def _expand_terms(text: str) -> set[str]:
    return set(tokenize(text)) | set(alias_tags(text))


def _gene_tokens(text: str) -> set[str]:
    """Heuristic gene/variant tokens: has a digit, or is an all-caps acronym."""

    return {
        token.lower()
        for token in GENE_TOKEN_RE.findall(text)
        if any(char.isdigit() for char in token) or (token.isupper() and len(token) >= 3)
    }


def _concepts_by_type(text: str, ontology: Ontology) -> dict[str, set[str]]:
    typed: dict[str, set[str]] = {"gene": set(), "drug": set(), "disease": set()}
    for concept_id in ontology.concept_ids(text):
        concept_type = ontology.concepts[concept_id].type
        if concept_type == "gene":
            typed["gene"].add(concept_id)
        elif concept_type in ("drug", "drug_class"):
            typed["drug"].add(concept_id)
        elif concept_type == "disease":
            typed["disease"].add(concept_id)
    return typed


def _evidence_tier(record: CorpusRecord) -> str:
    """Classify a record into an evidence tier from study design or text cues."""

    if record.study_design in TIER_WEIGHT:
        return record.study_design
    haystack = f"{record.abstract} {record.evidence_type}".lower()
    for tier, cues in _TIER_CUES:
        if any(cue in haystack for cue in cues):
            return tier
    if "association" in record.evidence_type:
        return "association"
    return "unspecified"


def build_evidence_card(
    query: str,
    retrieved: list[RetrievedRecord],
    *,
    claim: str | None = None,
    source: str = "sample",
    ontology: Ontology | None = None,
    extractor=None,
) -> EvidenceCard:
    ontology = ontology or Ontology.load()
    if extractor is not None:
        claims = extractor.extract(claim or query, retrieved)
    else:
        claims = extract_claims(claim or query, retrieved, ontology=ontology)
    measurements: list[QuantMeasurement] = []
    for item in retrieved:
        measurements.extend(
            extract_measurements(
                item.record.abstract, source_id=item.record.id, ontology=ontology
            )
        )
    return EvidenceCard(
        query=query,
        retrieved=retrieved,
        claims=claims,
        claim=claim,
        source=source,
        measurements=measurements,
        verdict=assess_verdict(claims),
        limitations=[
            "Uses toy/sample abstracts by default; optional PubMed mode uses public metadata.",
            "Deterministic stance labeling is a scaffold for a future model-backed extractor.",
            "Evidence labels are illustrative research signals, not clinical guidance.",
        ],
        next_checks=[
            "Review cited records manually before drawing scientific conclusions.",
            "Add model-based claim extraction with citation-grounded outputs.",
            "Evaluate evidence support with a curated benchmark.",
        ],
    )


def extract_claims(
    query: str,
    retrieved: list[RetrievedRecord],
    *,
    ontology: Ontology | None = None,
) -> list[EvidenceClaim]:
    ontology = ontology or Ontology.load()
    query_terms = _expand_terms(query)
    anchors = _claim_anchors(query, query_terms, ontology)
    claim_polarity = _outcome_polarity(query_terms)
    claims: list[EvidenceClaim] = []
    for item in retrieved:
        tier = _evidence_tier(item.record)
        for sentence, start, end in _sentence_spans(item.record.abstract):
            base_terms = set(tokenize(sentence))
            sentence_terms = base_terms | set(alias_tags(sentence))
            if len(query_terms & sentence_terms) < 2:
                continue
            sentence_genes = _gene_tokens(sentence)
            sentence_typed = _concepts_by_type(sentence, ontology)
            sentence_methods = base_terms & METHOD_TERMS
            grounded = _entity_grounded(sentence_genes, sentence_typed, anchors)
            anchor_categories = _anchor_category_count(
                sentence_genes, sentence_typed, sentence_methods, anchors
            )
            facets = _facets(base_terms)
            stance = _stance(
                sentence_terms,
                item.score,
                claim_polarity=claim_polarity,
                grounded=grounded,
                anchor_categories=anchor_categories,
                predicate_anchor=anchors["predicate"],
            )
            claims.append(
                EvidenceClaim(
                    text=sentence.strip(),
                    source_id=item.record.id,
                    evidence_type=item.record.evidence_type,
                    confidence=_confidence(
                        item.score,
                        stance=stance,
                        anchor_categories=anchor_categories,
                        facet_count=len(facets),
                        tier=tier,
                    ),
                    stance=stance,
                    facets=facets,
                    tier=tier,
                    start=start,
                    end=end,
                )
            )
    return claims


def _facets(terms: set[str]) -> tuple[str, ...]:
    return tuple(name for name, lexicon in FACETS.items() if terms & lexicon)


def assess_verdict(claims: list[EvidenceClaim]) -> Verdict:
    """Aggregate on-claim evidence into a tier-weighted, source-level verdict.

    Sources are counted once per stance (a record's tier is fixed), so many
    sentences from one weak study cannot outvote a single strong one. The net
    balance and the per-tier breakdown are both surfaced so the grade is auditable.
    """

    support: dict[str, str] = {}
    conflict: dict[str, str] = {}
    indirect = 0
    for claim in claims:
        if claim.stance == "supports":
            support[claim.source_id] = claim.tier
        elif claim.stance == "conflicts":
            conflict[claim.source_id] = claim.tier
        else:
            indirect += 1

    support_weight = sum(TIER_WEIGHT.get(tier, 0.5) for tier in support.values())
    conflict_weight = sum(TIER_WEIGHT.get(tier, 0.5) for tier in conflict.values())
    total = support_weight + conflict_weight

    if total < MIN_VERDICT_EVIDENCE:
        label = "insufficient"
        strength = 0.0
    else:
        balance = (support_weight - conflict_weight) / total
        strength = round(balance, 3)
        minority_share = min(support_weight, conflict_weight) / total
        if support_weight > 0 and conflict_weight > 0 and minority_share >= CONTESTED_SHARE:
            label = "contested"
        elif balance >= WELL_SUPPORTED_BALANCE:
            label = "well-supported"
        else:
            label = "mixed"

    rationale = (
        f"supports: {_tier_breakdown(support)}; "
        f"conflicts: {_tier_breakdown(conflict)}; "
        f"{indirect} indirect"
    )
    return Verdict(
        label=label,
        strength=strength,
        support_sources=len(support),
        conflict_sources=len(conflict),
        indirect_sentences=indirect,
        rationale=rationale,
    )


def _tier_breakdown(sources: dict[str, str]) -> str:
    if not sources:
        return "none"
    counts = Counter(sources.values())
    return ", ".join(f"{count}×{tier}" for tier, count in sorted(counts.items()))


def _append_verdict(lines: list[str], verdict: Verdict | None) -> None:
    if verdict is None:
        return
    lines.extend(
        [
            "",
            "## Verdict",
            f"- {verdict.label} (strength {verdict.strength:+.2f}) — {verdict.rationale}",
            "- Weighted by study-design tier over independent sources; not clinical guidance.",
        ]
    )


def _sentence_spans(text: str) -> list[tuple[str, int, int]]:
    """Split ``text`` into sentences while preserving character offsets.

    Offsets point at the trimmed sentence within the source abstract so each
    extracted claim carries verifiable provenance back to the record.
    """

    spans: list[tuple[str, int, int]] = []
    cursor = 0
    for match in SENTENCE_RE.finditer(text):
        spans.append(_trimmed_span(text, cursor, match.start()))
        cursor = match.end()
    spans.append(_trimmed_span(text, cursor, len(text)))
    return [span for span in spans if span[0]]


def _trimmed_span(text: str, start: int, end: int) -> tuple[str, int, int]:
    raw = text[start:end]
    lead = len(raw) - len(raw.lstrip())
    trail = len(raw) - len(raw.rstrip())
    return raw.strip(), start + lead, end - trail


def render_markdown(card: EvidenceCard) -> str:
    lines = [
        "# Evidence Card",
        "",
        f"Source: {card.source}",
        f"Query: {card.query}",
    ]
    if card.claim:
        lines.append(f"Claim: {card.claim}")

    _append_verdict(lines, card.verdict)

    lines.extend(["", "## Retrieved Evidence"])
    for item in card.retrieved:
        lines.append(
            f"- {item.record.id} ({item.record.year}) score={item.score}: {item.record.title}"
        )

    _append_claim_group(lines, "Supporting Evidence", card.claims, "supports")
    _append_claim_group(lines, "Conflicting Evidence", card.claims, "conflicts")
    _append_claim_group(lines, "Insufficient or Indirect Evidence", card.claims, "insufficient")
    _append_facet_view(lines, card.claims)
    _append_quant_view(lines, card.measurements)

    lines.extend(["", "## Limitations"])
    lines.extend(f"- {item}" for item in card.limitations)
    lines.extend(["", "## Next Checks"])
    lines.extend(f"- {item}" for item in card.next_checks)
    return "\n".join(lines)


def _confidence(
    score: float,
    *,
    stance: str,
    anchor_categories: int,
    facet_count: int,
    tier: str,
) -> str:
    """Grade evidence strength from relevance, decisiveness, grounding, and tier.

    Combines retrieval relevance with how decisively the sentence takes a stance,
    how many entity anchors it grounds against, how many evidence angles it
    covers, and the study-design tier, so the label reflects evidence quality
    rather than keyword overlap alone.
    """

    strength = min(score, 0.6)
    if stance in ("supports", "conflicts"):
        strength += 0.25
    strength += min(anchor_categories, 3) * 0.1
    strength += min(facet_count, 3) * 0.05
    strength += (TIER_WEIGHT.get(tier, 0.5) - 0.5) * 0.4
    if strength >= 0.75:
        return "high"
    if strength >= 0.45:
        return "medium"
    return "low"


def _stance(
    sentence_terms: set[str],
    score: float,
    *,
    claim_polarity: str | None,
    grounded: bool,
    anchor_categories: int,
    predicate_anchor: set[str],
) -> str:
    predicate_terms = predicate_anchor | PREDICATE_TERMS
    predicate_overlap = bool(sentence_terms & predicate_terms)
    strong_predicate_overlap = len(sentence_terms & predicate_terms) >= 2
    if INSUFFICIENT_CUES & sentence_terms or score < 0.3:
        return "insufficient"
    if (
        grounded
        and CONFLICT_CUES & sentence_terms
        and anchor_categories >= 2
        and predicate_overlap
    ):
        return "conflicts"
    if not grounded:
        return "insufficient"
    if (anchor_categories < 2 and not strong_predicate_overlap) or not predicate_overlap:
        return "insufficient"
    sentence_polarity = _outcome_polarity(sentence_terms)
    if claim_polarity and sentence_polarity and claim_polarity != sentence_polarity:
        return "insufficient"
    return "supports"


def _outcome_polarity(terms: set[str]) -> str | None:
    has_response = bool(terms & RESPONSE_CUES)
    has_resistance = bool(terms & RESISTANCE_CUES)
    if has_response and not has_resistance:
        return "response"
    if has_resistance and not has_response:
        return "resistance"
    return None


def _entity_grounded(
    sentence_genes: set[str],
    sentence_typed: dict[str, set[str]],
    anchors: dict[str, set[str]],
) -> bool:
    """Require the sentence to name the claim's principal entity.

    Grounding is checked by normalized concept identity (and gene tokens for
    variants the ontology does not carry), so it generalizes across domains
    instead of relying on an oncology-specific disease word list.
    """

    if anchors["gene"] or anchors["gene_concepts"]:
        return bool(sentence_genes & anchors["gene"]) or bool(
            sentence_typed["gene"] & anchors["gene_concepts"]
        )
    if anchors["disease"]:
        return bool(sentence_typed["disease"] & anchors["disease"])
    if anchors["therapy"]:
        return bool(sentence_typed["drug"] & anchors["therapy"])
    return True


def _claim_anchors(
    query: str, query_terms: set[str], ontology: Ontology
) -> dict[str, set[str]]:
    typed = _concepts_by_type(query, ontology)
    return {
        "gene": _gene_tokens(query),
        "gene_concepts": typed["gene"],
        "disease": typed["disease"],
        "therapy": typed["drug"],
        "method": query_terms & METHOD_TERMS,
        "predicate": query_terms & PREDICATE_TERMS,
    }


def _anchor_category_count(
    sentence_genes: set[str],
    sentence_typed: dict[str, set[str]],
    sentence_methods: set[str],
    anchors: dict[str, set[str]],
) -> int:
    count = 0
    if (sentence_genes & anchors["gene"]) or (
        sentence_typed["gene"] & anchors["gene_concepts"]
    ):
        count += 1
    if sentence_typed["disease"] & anchors["disease"]:
        count += 1
    if sentence_typed["drug"] & anchors["therapy"]:
        count += 1
    if sentence_methods & anchors["method"]:
        count += 1
    return count


def _append_claim_group(
    lines: list[str],
    heading: str,
    claims: list[EvidenceClaim],
    stance: str,
) -> None:
    lines.extend(["", f"## {heading}"])
    selected = _cap_per_source([claim for claim in claims if claim.stance == stance])
    if not selected:
        lines.append("- No extracted evidence in this category.")
        return
    for claim in selected:
        facets = ", ".join(claim.facets) or "general"
        provenance = f"{claim.source_id}@{claim.start}-{claim.end}"
        lines.append(
            f"- [{claim.confidence} | {claim.tier} | {claim.evidence_type} | {facets} | {provenance}] {claim.text}"
        )


def _append_facet_view(lines: list[str], claims: list[EvidenceClaim]) -> None:
    lines.extend(["", "## Evidence by Angle"])
    on_claim = [claim for claim in claims if claim.stance in ("supports", "conflicts")]
    printed = False
    for facet in FACETS:
        group = _cap_per_source([claim for claim in on_claim if facet in claim.facets])
        if not group:
            continue
        printed = True
        lines.append(f"- {facet}:")
        for claim in group:
            lines.append(f"  - [{claim.stance} | {claim.source_id}] {claim.text}")
    if not printed:
        lines.append("- No supporting or conflicting evidence to group by angle yet.")


def _append_quant_view(lines: list[str], measurements: list[QuantMeasurement]) -> None:
    lines.extend(["", "## Quantitative Evidence"])
    if not measurements:
        lines.append("- No quantitative parameters extracted.")
        return
    # Group by parameter and sort by value so compounds are directly comparable.
    by_parameter: dict[str, list[QuantMeasurement]] = {}
    for measurement in measurements:
        by_parameter.setdefault(measurement.parameter, []).append(measurement)
    for parameter in sorted(by_parameter):
        lines.append(f"- {parameter}:")
        for measurement in sorted(by_parameter[parameter], key=lambda m: m.value):
            entity = measurement.primary_entity or "unattributed"
            provenance = f"{measurement.source_id}@{measurement.start}-{measurement.end}"
            relation = "" if measurement.relation == "=" else measurement.relation
            lines.append(
                f"  - {entity}: {relation}{measurement.value:g} {measurement.unit} [{provenance}]"
            )


def _cap_per_source(claims: list[EvidenceClaim]) -> list[EvidenceClaim]:
    counts: dict[str, int] = {}
    capped: list[EvidenceClaim] = []
    for claim in claims:
        count = counts.get(claim.source_id, 0)
        if count >= MAX_SENTENCES_PER_SOURCE_STANCE:
            continue
        capped.append(claim)
        counts[claim.source_id] = count + 1
    return capped
