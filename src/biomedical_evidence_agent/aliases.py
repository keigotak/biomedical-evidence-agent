from __future__ import annotations

import re

# Small, illustrative biomedical alias map. Each group maps several surface
# forms (abbreviations, full names, drug/class synonyms) to one canonical tag
# token. Expanding both queries and documents with the canonical token lets a
# claim written with abbreviations retrieve and ground against records that
# spell the terms out in full. This is a demo scaffold, not an ontology.
ALIAS_GROUPS: list[tuple[str, list[str]]] = [
    ("nsclc", ["nsclc", "non-small cell lung cancer", "non small cell lung cancer"]),
    ("inhibitor", ["tki", "tkis", "tyrosine kinase inhibitor", "tyrosine kinase inhibitors"]),
    ("egfr", ["egfr inhibitor", "egfr inhibitors", "erlotinib", "osimertinib", "gefitinib"]),
    ("braf", ["braf inhibitor", "vemurafenib", "dabrafenib"]),
    ("targeted", ["targeted therapy", "targeted inhibitor", "targeted inhibitors"]),
]

_ALIAS_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        canonical,
        re.compile(r"\b(?:" + "|".join(re.escape(form) for form in forms) + r")\b", re.IGNORECASE),
    )
    for canonical, forms in ALIAS_GROUPS
]


def alias_tags(text: str) -> list[str]:
    """Return canonical alias tags for every alias group matched in ``text``."""

    return [canonical for canonical, pattern in _ALIAS_PATTERNS if pattern.search(text)]
