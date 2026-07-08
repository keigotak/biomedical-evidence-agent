from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Concept:
    """A normalized biomedical concept with a local id and external cross-refs.

    The local ``id`` (``BEA:<type>:<slug>``) is the stable resolution unit used
    across retrieval, attribution, and evaluation. ``xrefs`` map that local id to
    external authorities (UniProt, ChEMBL, MeSH, HGNC) so the registry can later
    be swapped for a real ontology service without changing the id contract.
    """

    id: str
    type: str
    canonical: str
    surface_forms: tuple[str, ...] = ()
    xrefs: dict[str, str] = field(default_factory=dict)
    targets: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConceptMatch:
    """A concept resolved to a character span in a source text."""

    concept: Concept
    surface: str
    start: int
    end: int


@dataclass(frozen=True)
class CorpusRecord:
    id: str
    title: str
    year: int
    entities: dict[str, list[str]]
    abstract: str
    evidence_type: str
    study_design: str = ""


@dataclass(frozen=True)
class RetrievedRecord:
    record: CorpusRecord
    score: float


@dataclass(frozen=True)
class EvidenceClaim:
    text: str
    source_id: str
    evidence_type: str
    confidence: str
    stance: str = "insufficient"
    facets: tuple[str, ...] = ()
    tier: str = "unspecified"
    start: int = 0
    end: int = 0


@dataclass(frozen=True)
class QuantMeasurement:
    """A quantitative pharmacology parameter extracted from a source sentence.

    Captures potency and PK values (IC50, EC50, Ki, Cmax, half-life, ...) with
    their relation and unit, plus the compound/target context they belong to, so
    values are comparable across compounds and assays instead of buried in prose.
    """

    parameter: str
    relation: str
    value: float
    unit: str
    source_id: str
    primary_entity: str | None = None
    entity_ids: tuple[str, ...] = ()
    start: int = 0
    end: int = 0
    raw: str = ""


@dataclass(frozen=True)
class MoaRelation:
    """A grounded drug→target mechanism-of-action relation extracted from text.

    ``mechanism`` is ``agonist`` / ``antagonist`` (the directional call the text
    supports), attributed to a drug on its ontology-declared target so the
    relation is grounded by concept identity rather than surface co-occurrence.
    """

    drug_id: str
    drug_name: str
    target_id: str
    target_name: str
    mechanism: str
    source_id: str
    quote: str
    start: int
    end: int


@dataclass(frozen=True)
class DossierCompound:
    """A modulator of a target, with any quantitative evidence against it."""

    concept_id: str
    name: str
    declared_target: bool
    measurements: tuple[QuantMeasurement, ...] = ()
    verdict: "Verdict | None" = None
    mechanism: str = ""


@dataclass(frozen=True)
class TargetDossier:
    """A target-centric roll-up: everything the corpus says about one target.

    Pivots from a single claim to a normalized target concept and aggregates the
    modulators, disease contexts, evidence angles, and study tiers across every
    record that mentions it — the entity normalization backbone made queryable.
    """

    target_id: str
    target_name: str
    xrefs: dict[str, str]
    record_ids: tuple[str, ...]
    compounds: tuple[DossierCompound, ...]
    diseases: tuple[str, ...]
    angles: dict[str, tuple[str, ...]]
    tiers: dict[str, int]
    indication_verdicts: dict[str, "Verdict"] = field(default_factory=dict)


@dataclass(frozen=True)
class Verdict:
    """A weighted assessment of a claim from its supporting/conflicting evidence.

    ``strength`` is the tier-weighted balance in [-1, 1] (positive = net support),
    computed over independent sources rather than sentence counts. ``label`` is the
    reader-facing grade; ``rationale`` shows the breakdown so the number is auditable.
    """

    label: str
    strength: float
    support_sources: int
    conflict_sources: int
    indirect_sentences: int
    rationale: str


@dataclass(frozen=True)
class EvidenceCard:
    query: str
    retrieved: list[RetrievedRecord]
    claims: list[EvidenceClaim]
    claim: str | None = None
    source: str = "sample"
    limitations: list[str] = field(default_factory=list)
    next_checks: list[str] = field(default_factory=list)
    measurements: list[QuantMeasurement] = field(default_factory=list)
    verdict: "Verdict | None" = None
