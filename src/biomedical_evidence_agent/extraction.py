from __future__ import annotations

import json
from typing import Callable

from .evidence import (
    _concepts_by_type,
    _confidence,
    _evidence_tier,
    _facets,
    _sentence_spans,
)
from .ontology import Ontology
from .retrieval import tokenize
from .schemas import CorpusRecord, EvidenceClaim, RetrievedRecord

# Model-backed claim extraction. This is the interface the README predicts: the
# deterministic `extract_claims` scaffold can be swapped for a model that reads
# the abstract and emits stance-labeled claims — as long as every claim is a
# VERBATIM span of its source, verified here rather than trusted. The model call
# is injected as a `responder`, so a real Anthropic backend and an offline mock
# share the same grounding + faithfulness pipeline.

STANCES = ("supports", "conflicts", "insufficient")
DEFAULT_MODEL = "claude-opus-4-8"

# responder(claim, record) -> list of {"quote", "stance", "rationale"}
Responder = Callable[[str, CorpusRecord], list[dict]]

EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "quote": {"type": "string"},
                    "stance": {"type": "string", "enum": list(STANCES)},
                    "rationale": {"type": "string"},
                },
                "required": ["quote", "stance", "rationale"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}

_SYSTEM_PROMPT = (
    "You are a biomedical evidence extractor. Given a claim and a source "
    "abstract, extract the sentences from the abstract that bear on the claim. "
    "Quote each sentence VERBATIM from the abstract — never paraphrase or edit. "
    "Label each with a stance relative to the claim: 'supports', 'conflicts', or "
    "'insufficient' (indirect or hedged). Only use text present in the abstract."
)


class ExtractorUnavailable(RuntimeError):
    """Raised when the optional model-backed extractor cannot be initialized."""


class LLMClaimExtractor:
    """Turns a responder's raw quotes into grounded, verifiable EvidenceClaims.

    The faithfulness guard is the core: a quote is kept only if it is a verbatim
    span of the cited abstract. Hallucinated or altered quotes are dropped, so a
    model can be swapped in without weakening the card's provenance guarantee.
    """

    def __init__(self, *, responder: Responder, ontology: Ontology | None = None):
        self._responder = responder
        self._ontology = ontology or Ontology.load()

    def extract(self, claim: str, retrieved: list[RetrievedRecord]) -> list[EvidenceClaim]:
        claims, _proposed = self.extract_with_stats(claim, retrieved)
        return claims

    def extract_with_stats(
        self, claim: str, retrieved: list[RetrievedRecord]
    ) -> tuple[list[EvidenceClaim], int]:
        """Return grounded claims and the number of raw quotes proposed.

        The proposed count minus ``len(claims)`` is how many quotes failed the
        faithfulness check — the signal a faithfulness metric reports on.
        """

        claims: list[EvidenceClaim] = []
        proposed = 0
        for item in retrieved:
            for raw in self._responder(claim, item.record) or []:
                proposed += 1
                grounded = self._ground(raw, item)
                if grounded is not None:
                    claims.append(grounded)
        return claims, proposed

    def _ground(self, raw: dict, item: RetrievedRecord) -> EvidenceClaim | None:
        quote = (raw.get("quote") or "").strip()
        if not quote:
            return None
        start = item.record.abstract.find(quote)
        if start < 0:
            return None  # faithfulness guard: not a verbatim span of the source
        stance = raw.get("stance")
        if stance not in STANCES:
            stance = "insufficient"
        tier = _evidence_tier(item.record)
        facets = _facets(set(tokenize(quote)))
        typed = _concepts_by_type(quote, self._ontology)
        anchor_categories = sum(
            1 for category in ("gene", "drug", "disease") if typed[category]
        )
        return EvidenceClaim(
            text=quote,
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
            end=start + len(quote),
        )


def anthropic_responder(*, model: str = DEFAULT_MODEL, api_key: str | None = None) -> Responder:
    """Real backend: one structured-output call per record, quotes verbatim.

    Behind the optional ``llm`` extra. Raises ExtractorUnavailable (rather than a
    deep ImportError/auth error) when the SDK or credentials are missing, so the
    default deterministic workflow stays dependency-free.
    """

    try:
        import anthropic
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ExtractorUnavailable(
            "LLM extraction requires the optional 'llm' extra. "
            "Install it with: pip install '.[llm]'"
        ) from exc
    try:
        client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()
    except Exception as exc:  # pragma: no cover - depends on credential config
        raise ExtractorUnavailable(
            f"Anthropic client unavailable (set ANTHROPIC_API_KEY): {exc}"
        ) from exc

    def respond(claim: str, record: CorpusRecord) -> list[dict]:
        prompt = (
            f"Claim:\n{claim}\n\nSource abstract ({record.id}):\n{record.abstract}"
        )
        message = client.messages.create(
            model=model,
            max_tokens=16000,
            system=_SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": EXTRACTION_SCHEMA}},
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((block.text for block in message.content if block.type == "text"), "")
        data = json.loads(text) if text else {}
        return list(data.get("claims", []))

    return respond


def heuristic_responder(*, ontology: Ontology | None = None) -> Responder:
    """Offline stand-in for the model, so the whole path runs without a key.

    It returns verbatim sentences that share entities/terms with the claim and a
    naive stance. It is NOT a substitute for a real model's judgment — it exists
    to exercise grounding, the faithfulness guard, the card, and evaluation
    end-to-end offline. Extraction quality tracks the responder, not this scaffold.
    """

    ontology = ontology or Ontology.load()
    conflict_cues = {"not", "no", "without", "failed", "lack", "negative"}

    def respond(claim: str, record: CorpusRecord) -> list[dict]:
        claim_terms = set(tokenize(claim))
        claim_concepts = set(ontology.concept_ids(claim))
        out: list[dict] = []
        for sentence, _start, _end in _sentence_spans(record.abstract):
            terms = set(tokenize(sentence))
            shares_terms = len(claim_terms & terms) >= 2
            shares_concept = bool(claim_concepts & set(ontology.concept_ids(sentence)))
            if not (shares_terms or shares_concept):
                continue
            stance = "conflicts" if conflict_cues & terms else "supports"
            out.append(
                {
                    "quote": sentence,
                    "stance": stance,
                    "rationale": "shares entities or terms with the claim",
                }
            )
        return out

    return respond
