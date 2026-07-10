from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import data_path
from .schemas import Concept, ConceptMatch

# Surface forms are matched on token boundaries that read hyphenated compounds
# the way a person does. A preceding word char never matches (no run-on like
# ``xEGFR``). A preceding hyphen is allowed — so a qualifying prefix that keeps the
# entity (``anti-EGFR``, ``pan-EGFR``) links it — EXCEPT the negating prefixes
# ``non-`` / ``un-`` (``non-EGFR`` means *not* EGFR), which stay blocked. The RIGHT
# side allows a trailing hyphen, so a suffix descriptor that still denotes the
# entity (``EGFR-mutant``, ``BRAF-V600E``, ``TP53-null``) links it too.
_BOUNDARY_LEFT = r"(?<!\w)(?<!non-)(?<!un-)"
_BOUNDARY_RIGHT = r"(?!\w)"


def default_ontology_path() -> Path:
    return data_path("ontology.jsonl")


class Ontology:
    """A curated concept registry with longest-match, type-aware normalization.

    This is a demo scaffold, not a full terminology service. It exists to give
    evidence integration a stable same-entity guarantee: two mentions link to
    the same concept id if and only if they denote the same entity, regardless
    of abbreviation, synonym, or brand/generic surface form.
    """

    def __init__(self, concepts: list[Concept]):
        self.concepts = {concept.id: concept for concept in concepts}
        self._matchers = self._build_matchers(concepts)

    @classmethod
    def load(cls, path: Path | None = None) -> "Ontology":
        path = path or default_ontology_path()
        concepts: list[Concept] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                item = json.loads(line)
                concepts.append(
                    Concept(
                        id=item["id"],
                        type=item["type"],
                        canonical=item["canonical"],
                        surface_forms=tuple(item.get("surface_forms", [])),
                        xrefs=dict(item.get("xrefs", {})),
                        targets=tuple(item.get("targets", [])),
                    )
                )
        return cls(concepts)

    @staticmethod
    def _build_matchers(
        concepts: list[Concept],
    ) -> list[tuple[int, Concept, re.Pattern[str]]]:
        matchers: list[tuple[int, Concept, re.Pattern[str]]] = []
        for concept in concepts:
            for form in concept.surface_forms:
                pattern = re.compile(
                    _BOUNDARY_LEFT + re.escape(form.lower()) + _BOUNDARY_RIGHT
                )
                matchers.append((len(form), concept, pattern))
        # Longest forms first so overlap resolution keeps the most specific span.
        matchers.sort(key=lambda entry: entry[0], reverse=True)
        return matchers

    def normalize(self, text: str) -> list[ConceptMatch]:
        """Return non-overlapping concept matches, preferring the longest span."""

        lowered = text.lower()
        candidates: list[ConceptMatch] = []
        for _length, concept, pattern in self._matchers:
            for match in pattern.finditer(lowered):
                candidates.append(
                    ConceptMatch(
                        concept=concept,
                        surface=text[match.start() : match.end()],
                        start=match.start(),
                        end=match.end(),
                    )
                )
        candidates.sort(key=lambda item: (item.start, -(item.end - item.start)))
        resolved: list[ConceptMatch] = []
        occupied: list[tuple[int, int]] = []
        for candidate in candidates:
            if any(
                candidate.start < end and candidate.end > start
                for start, end in occupied
            ):
                continue
            resolved.append(candidate)
            occupied.append((candidate.start, candidate.end))
        resolved.sort(key=lambda item: item.start)
        return resolved

    def concept_ids(self, text: str) -> list[str]:
        """Return the distinct concept ids grounded in ``text``, in reading order."""

        ordered: list[str] = []
        for match in self.normalize(text):
            if match.concept.id not in ordered:
                ordered.append(match.concept.id)
        return ordered
