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
                r"(?<![A-Za-z0-9])(?:" + pattern + r")(?![A-Za-z0-9])", re.IGNORECASE
            )
            for param_match in regex.finditer(sentence):
                window = sentence[param_match.end() : param_match.end() + _WINDOW]
                value_match = _VALUE_RE.search(window)
                if not value_match:
                    continue
                unit = value_match.group("unit")
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
