from __future__ import annotations

import re

from .ontology import Ontology
from .schemas import QuantMeasurement

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Quantitative pharmacology parameters. Each entry pairs a canonical name with a
# surface pattern; potency (IC50/EC50/Ki/Kd) and PK/exposure (Cmax/AUC/half-life/
# clearance/bioavailability) are the values a pharmacology reader compares across
# compounds, so they are what we lift out of prose into structured records.
PARAM_PATTERNS: list[tuple[str, str]] = [
    ("IC50", r"ic\s*50"),
    ("EC50", r"ec\s*50"),
    ("GI50", r"gi\s*50"),
    ("Kd", r"kd"),
    ("Ki", r"ki"),
    ("Cmax", r"c\s*max"),
    ("AUC", r"auc"),
    ("half-life", r"half[-\s]?life|t1/2|t½"),
    ("clearance", r"clearance"),
    ("bioavailability", r"bioavailability"),
]

_UNIT_ALT = (
    r"nM|pM|mM|µM|uM|μM|ng/mL|µg/mL|ug/mL|mg/kg|mg/mL|mg|kg|"
    r"hours|hrs|hr|h|min|%|M"
)
_VALUE_RE = re.compile(
    r"(?P<rel>[<>=≈~]|≤|≥)?\s*(?P<val>\d+(?:\.\d+)?)\s*(?P<unit>" + _UNIT_ALT + r")(?![A-Za-z])"
)
_UNIT_CANON = {
    "uM": "µM",
    "μM": "µM",
    "ug/mL": "µg/mL",
    "hr": "h",
    "hrs": "h",
    "hours": "h",
}
_ENTITY_TYPES = ("drug", "drug_class", "gene")
_WINDOW = 40

# Units that are physically plausible for a parameter, keyed by canonical unit.
# A parameter absent from this map accepts any unit (e.g. Cmax/AUC/clearance,
# whose units vary). Potency/affinity are concentrations; a "Ki" reported in mg
# or % is a misread (a reagent mass, or "Ki-67" the proliferation marker), so it
# is rejected rather than emitted.
_CONCENTRATION = {"nM", "pM", "mM", "µM", "M", "ng/mL", "µg/mL"}
_TIME = {"h", "min"}
_ALLOWED_UNITS = {
    "IC50": _CONCENTRATION,
    "EC50": _CONCENTRATION,
    "GI50": _CONCENTRATION,
    "Ki": _CONCENTRATION,
    "Kd": _CONCENTRATION,
    "half-life": _TIME,
    "bioavailability": {"%"},
}
# A value negated before it is stated ("was not reached at 100 nM") asserts the
# opposite; abstain rather than record the wrong number.
_NEGATION = {"not", "no", "without", "never", "unable", "unavailable", "fail", "failed", "fails"}
_WORD_RE = re.compile(r"[a-z]+")


def _sentence_spans(text: str) -> list[tuple[str, int]]:
    spans: list[tuple[str, int]] = []
    cursor = 0
    for match in SENTENCE_RE.finditer(text):
        spans.append((text[cursor : match.start()], cursor))
        cursor = match.end()
    spans.append((text[cursor:], cursor))
    return [(sentence, offset) for sentence, offset in spans if sentence.strip()]


def extract_measurements(
    text: str,
    *,
    source_id: str = "",
    ontology: Ontology | None = None,
) -> list[QuantMeasurement]:
    """Extract quantitative parameters with value, unit, and compound context."""

    ontology = ontology or Ontology.load()
    measurements: list[QuantMeasurement] = []
    for sentence, sentence_offset in _sentence_spans(text):
        entity_spans = [
            match
            for match in ontology.normalize(sentence)
            if match.concept.type in _ENTITY_TYPES
        ]
        entity_ids = tuple(dict.fromkeys(match.concept.id for match in entity_spans))
        for name, pattern in PARAM_PATTERNS:
            regex = re.compile(
                r"(?<![A-Za-z0-9-])(?:" + pattern + r")(?![A-Za-z0-9-])", re.IGNORECASE
            )
            for param_match in regex.finditer(sentence):
                window = sentence[param_match.end() : param_match.end() + _WINDOW]
                value_match = _VALUE_RE.search(window)
                if not value_match:
                    continue
                # Skip if the value is negated before it is stated.
                if set(_WORD_RE.findall(window[: value_match.start()].lower())) & _NEGATION:
                    continue
                unit = value_match.group("unit")
                canonical_unit = _UNIT_CANON.get(unit, unit)
                allowed = _ALLOWED_UNITS.get(name)
                if allowed is not None and canonical_unit not in allowed:
                    continue
                primary = _primary_entity(entity_spans, param_match.start())
                measurements.append(
                    QuantMeasurement(
                        parameter=name,
                        relation=value_match.group("rel") or "=",
                        value=float(value_match.group("val")),
                        unit=_UNIT_CANON.get(unit, unit),
                        source_id=source_id,
                        primary_entity=primary,
                        entity_ids=entity_ids,
                        start=sentence_offset + param_match.start(),
                        end=sentence_offset
                        + param_match.end()
                        + value_match.end(),
                        raw=f"{param_match.group()} {value_match.group().strip()}",
                    )
                )
    return measurements


def _primary_entity(entity_spans, position: int) -> str | None:
    """Nearest preceding drug (else nearest drug/gene) to a parameter mention."""

    drugs = [m for m in entity_spans if m.concept.type in ("drug", "drug_class")]
    preceding_drugs = [m for m in drugs if m.start <= position]
    if preceding_drugs:
        return max(preceding_drugs, key=lambda m: m.start).concept.canonical
    if drugs:
        return min(drugs, key=lambda m: abs(m.start - position)).concept.canonical
    if entity_spans:
        return min(entity_spans, key=lambda m: abs(m.start - position)).concept.canonical
    return None
