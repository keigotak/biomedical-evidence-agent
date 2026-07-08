from __future__ import annotations

import re

from .ontology import Ontology
from .schemas import MoaRelation

SENTENCE_RE = re.compile(r"(?<=[.!?])\s+")

# Directional mechanism cues. A drug that *activates/agonizes* its target is an
# agonist; one that *inhibits/blocks/antagonizes* it is an antagonist. Cues are
# matched as whole words against the sentence so "activation" and "inhibitor"
# both count while substrings do not.
AGONIST_CUES = frozenset(
    {
        "agonist",
        "agonists",
        "agonize",
        "agonized",
        "agonizes",
        "activate",
        "activated",
        "activates",
        "activation",
        "stimulate",
        "stimulated",
        "stimulates",
        "stimulation",
    }
)
ANTAGONIST_CUES = frozenset(
    {
        "antagonist",
        "antagonists",
        "antagonize",
        "antagonized",
        "antagonizes",
        "inhibit",
        "inhibited",
        "inhibits",
        "inhibitor",
        "inhibitors",
        "inhibition",
        "block",
        "blocked",
        "blocks",
        "blockade",
        "suppress",
        "suppressed",
        "suppresses",
        "suppression",
    }
)

_WORD_RE = re.compile(r"[a-z0-9]+")


def _sentence_spans(text: str) -> list[tuple[str, int]]:
    spans: list[tuple[str, int]] = []
    cursor = 0
    for match in SENTENCE_RE.finditer(text):
        spans.append((text[cursor : match.start()], cursor))
        cursor = match.end()
    spans.append((text[cursor:], cursor))
    return [(sentence, offset) for sentence, offset in spans if sentence.strip()]


# A negated directional cue ("did not inhibit") reverses the mechanism; abstain
# rather than assert the opposite of what the sentence says.
NEGATION_CUES = frozenset(
    {"not", "no", "never", "without", "fails", "failed", "fail",
     "cannot", "unable", "lacks", "lack", "neither", "nor"}
)


def _mechanism_from_cues(words: set[str]) -> str:
    if words & NEGATION_CUES:
        return ""
    agonist = bool(words & AGONIST_CUES)
    antagonist = bool(words & ANTAGONIST_CUES)
    if agonist and not antagonist:
        return "agonist"
    if antagonist and not agonist:
        return "antagonist"
    return ""


def extract_moa(
    text: str,
    *,
    source_id: str = "",
    ontology: Ontology | None = None,
) -> list[MoaRelation]:
    """Extract grounded drug→target mechanism-of-action relations.

    A relation is emitted only when, within one sentence, a drug concept and one
    of its ontology-declared target genes both appear and the sentence carries an
    unambiguous directional cue. Requiring the *declared* target (concept
    identity) means a bare "EGFR activating variants" — a gene activated with no
    drug subject — yields nothing, and a drug is never paired with a co-mentioned
    gene it does not actually target.
    """

    ontology = ontology or Ontology.load()
    relations: list[MoaRelation] = []
    for sentence, offset in _sentence_spans(text):
        words = {match.group() for match in _WORD_RE.finditer(sentence.lower())}
        mechanism = _mechanism_from_cues(words)
        if not mechanism:
            continue
        # Trim so the provenance span slices back to the exact quote.
        quote = sentence.strip()
        start = offset + (len(sentence) - len(sentence.lstrip()))
        end = start + len(quote)
        matches = ontology.normalize(sentence)
        genes = {m.concept.id for m in matches if m.concept.type == "gene"}
        if not genes:
            continue
        for match in matches:
            concept = match.concept
            if concept.type not in ("drug", "drug_class"):
                continue
            targets_here = [t for t in concept.targets if t in genes]
            for target_id in targets_here:
                relations.append(
                    MoaRelation(
                        drug_id=concept.id,
                        drug_name=concept.canonical,
                        target_id=target_id,
                        target_name=ontology.concepts[target_id].canonical,
                        mechanism=mechanism,
                        source_id=source_id,
                        quote=quote,
                        start=start,
                        end=end,
                    )
                )
    return relations


def roll_up_mechanism(relations: list[MoaRelation], drug_id: str) -> str:
    """Collapse a drug's extracted mechanisms into one label.

    Returns the agreed mechanism, ``"mixed"`` if records disagree, or ``""`` when
    no directional relation was extracted for the drug.
    """

    mechanisms = {r.mechanism for r in relations if r.drug_id == drug_id}
    if not mechanisms:
        return ""
    if len(mechanisms) == 1:
        return next(iter(mechanisms))
    return "mixed"
