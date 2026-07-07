from __future__ import annotations

from .evidence import FACETS, _evidence_tier, build_evidence_card
from .ontology import Ontology
from .quant import extract_measurements
from .retrieval import ConceptAwareRetriever, tokenize
from .schemas import CorpusRecord, DossierCompound, TargetDossier, Verdict

_DRUG_TYPES = ("drug", "drug_class")


class DossierError(ValueError):
    """Raised when a target cannot be resolved to a concept."""


def _record_text(record: CorpusRecord) -> str:
    entity_text = " ".join(value for values in record.entities.values() for value in values)
    return f"{record.title} {entity_text} {record.abstract}"


def build_target_dossier(
    target: str,
    records: list[CorpusRecord],
    *,
    ontology: Ontology | None = None,
) -> TargetDossier:
    """Aggregate everything the corpus says about one normalized target.

    The target string is normalized to a concept, records are matched by concept
    identity (not surface text), and modulators/diseases/angles/tiers are rolled
    up across the matched records.
    """

    ontology = ontology or Ontology.load()
    target_concept = _resolve_target(target, ontology)

    matched = [
        record
        for record in records
        if target_concept.id in ontology.concept_ids(_record_text(record))
    ]

    measurements = [
        measurement
        for record in matched
        for measurement in extract_measurements(
            record.abstract, source_id=record.id, ontology=ontology
        )
    ]

    compounds = _collect_compounds(target_concept.id, matched, measurements, ontology)
    diseases = _collect_by_type(matched, ontology, "disease")
    angles = _collect_angles(matched)
    tiers = _collect_tiers(matched)
    indication_verdicts = _indication_verdicts(
        target_concept.canonical, diseases, records, ontology
    )

    return TargetDossier(
        target_id=target_concept.id,
        target_name=target_concept.canonical,
        xrefs=dict(target_concept.xrefs),
        record_ids=tuple(record.id for record in matched),
        compounds=compounds,
        diseases=diseases,
        angles=angles,
        tiers=tiers,
        indication_verdicts=indication_verdicts,
    )


def _indication_verdicts(
    target_name: str,
    diseases: tuple[str, ...],
    records: list[CorpusRecord],
    ontology: Ontology,
    *,
    top_k: int = 5,
) -> dict[str, Verdict]:
    """Run the claim pipeline per target–disease pair to grade target validation.

    This is verdict × dossier: for each indication the target appears in, a
    synthesized association claim is retrieved, extracted, and scored, so the
    dossier answers "is this target validated here, and how strongly" — with the
    same tier-weighted, source-level verdict used for a standalone claim.
    """

    retriever = ConceptAwareRetriever(records, ontology)
    verdicts: dict[str, Verdict] = {}
    for disease in diseases:
        claim = (
            f"{target_name} is associated with response to targeted therapy in {disease}."
        )
        ranked = retriever.search(claim, top_k=top_k)
        card = build_evidence_card(
            query=claim, retrieved=ranked, claim=claim, ontology=ontology
        )
        if card.verdict is not None:
            verdicts[disease] = card.verdict
    return verdicts


def _resolve_target(target: str, ontology: Ontology):
    matches = ontology.normalize(target)
    # Prefer a gene/protein target; fall back to the first resolved concept.
    for match in matches:
        if match.concept.type == "gene":
            return match.concept
    if matches:
        return matches[0].concept
    raise DossierError(f"Could not resolve a target concept from {target!r}.")


def _collect_compounds(
    target_id: str,
    matched: list[CorpusRecord],
    measurements: list,
    ontology: Ontology,
) -> tuple[DossierCompound, ...]:
    declared = {
        concept.id
        for concept in ontology.concepts.values()
        if concept.type in _DRUG_TYPES and target_id in concept.targets
    }
    co_mentioned = {
        concept_id
        for record in matched
        for concept_id in ontology.concept_ids(_record_text(record))
        if ontology.concepts[concept_id].type in _DRUG_TYPES
    }
    compounds: list[DossierCompound] = []
    for concept_id in sorted(declared | co_mentioned):
        concept = ontology.concepts[concept_id]
        # Keep declared modulators and specific co-mentioned drugs; drop generic
        # co-mentioned classes ("targeted therapy") that aren't declared here.
        if concept_id not in declared and concept.type != "drug":
            continue
        attached = tuple(
            measurement
            for measurement in measurements
            if measurement.primary_entity == concept.canonical
        )
        compounds.append(
            DossierCompound(
                concept_id=concept_id,
                name=concept.canonical,
                declared_target=concept_id in declared,
                measurements=attached,
            )
        )
    return tuple(compounds)


def _collect_by_type(
    matched: list[CorpusRecord], ontology: Ontology, concept_type: str
) -> tuple[str, ...]:
    names: list[str] = []
    for record in matched:
        for concept_id in ontology.concept_ids(_record_text(record)):
            concept = ontology.concepts[concept_id]
            if concept.type == concept_type and concept.canonical not in names:
                names.append(concept.canonical)
    return tuple(names)


def _collect_angles(matched: list[CorpusRecord]) -> dict[str, tuple[str, ...]]:
    angles: dict[str, list[str]] = {facet: [] for facet in FACETS}
    for record in matched:
        terms = set(tokenize(record.abstract))
        for facet, lexicon in FACETS.items():
            if terms & lexicon:
                angles[facet].append(record.id)
    return {facet: tuple(ids) for facet, ids in angles.items() if ids}


def _collect_tiers(matched: list[CorpusRecord]) -> dict[str, int]:
    tiers: dict[str, int] = {}
    for record in matched:
        tier = _evidence_tier(record)
        tiers[tier] = tiers.get(tier, 0) + 1
    return tiers


def render_dossier(dossier: TargetDossier) -> str:
    xrefs = ", ".join(f"{key}={value}" for key, value in sorted(dossier.xrefs.items()))
    lines = [
        f"# Target Dossier: {dossier.target_name} ({dossier.target_id})",
        "",
        f"External refs: {xrefs or 'none'}",
        f"Records mentioning target: {len(dossier.record_ids)}"
        + (f" ({', '.join(dossier.record_ids)})" if dossier.record_ids else ""),
        "",
        "## Modulators",
    ]
    if not dossier.compounds:
        lines.append("- None found in the corpus.")
    for compound in dossier.compounds:
        tag = " [declared target]" if compound.declared_target else ""
        potency = "; ".join(
            f"{m.parameter} {'' if m.relation == '=' else m.relation}{m.value:g} {m.unit}"
            f" [{m.source_id}@{m.start}-{m.end}]"
            for m in compound.measurements
        )
        lines.append(f"- {compound.name}{tag}" + (f" — {potency}" if potency else ""))

    lines.extend(["", "## Indication Evidence"])
    if not dossier.diseases:
        lines.append("- None found.")
    for name in dossier.diseases:
        verdict = dossier.indication_verdicts.get(name)
        if verdict is None:
            lines.append(f"- {name}")
        else:
            lines.append(
                f"- {name}: {verdict.label} (strength {verdict.strength:+.2f}) "
                f"— {verdict.rationale}"
            )

    lines.extend(["", "## Evidence by Angle"])
    if not dossier.angles:
        lines.append("- No angle-tagged evidence.")
    for facet, ids in dossier.angles.items():
        lines.append(f"- {facet}: {', '.join(ids)}")

    lines.extend(["", "## Evidence Tiers"])
    if not dossier.tiers:
        lines.append("- None.")
    for tier, count in sorted(dossier.tiers.items()):
        lines.append(f"- {tier}: {count}")

    lines.extend(
        [
            "",
            "## Limitations",
            "- Aggregated from toy/sample records; ontology xref ids are illustrative.",
            "- A research-signal roll-up, not a validated target assessment or clinical guidance.",
        ]
    )
    return "\n".join(lines)
