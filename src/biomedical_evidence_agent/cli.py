from __future__ import annotations

import argparse
import json
from pathlib import Path

from .evidence import build_evidence_card, render_markdown
from .paths import data_path
from .pubmed import PubMedError, search_pubmed
from .retrieval import ConceptAwareRetriever, LexicalRetriever, load_corpus
from .schemas import RetrievedRecord


def default_corpus_path() -> Path:
    return data_path("sample_corpus.jsonl")


def _build_retriever(name: str, records):
    if name == "lexical":
        return LexicalRetriever(records)
    if name == "embedding":
        from .embedding import EmbeddingRetriever, EmbeddingUnavailable

        try:
            return EmbeddingRetriever(records)
        except EmbeddingUnavailable as exc:
            raise SystemExit(str(exc)) from exc
    return ConceptAwareRetriever(records)


def _build_extractor(name: str):
    if name == "deterministic":
        return None
    from .extraction import LLMClaimExtractor, ExtractorUnavailable, heuristic_responder

    if name == "mock-llm":
        return LLMClaimExtractor(responder=heuristic_responder())
    from .extraction import anthropic_responder

    try:
        return LLMClaimExtractor(responder=anthropic_responder())
    except ExtractorUnavailable as exc:
        raise SystemExit(str(exc)) from exc


def _build_reviewer(name: str):
    if name == "none":
        return None
    from .reviewer import ReviewerUnavailable, anthropic_reviewer, mock_reviewer

    if name == "mock":
        return mock_reviewer()
    try:
        return anthropic_reviewer()
    except ReviewerUnavailable as exc:
        raise SystemExit(str(exc)) from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a biomedical evidence card.")
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--query", help="Biomedical evidence question or topic.")
    query_group.add_argument("--claim", help="Biomedical claim to review against retrieved evidence.")
    query_group.add_argument(
        "--target",
        help="Build a target-centric dossier (local corpus only), e.g. 'EGFR'.",
    )
    parser.add_argument("--top-k", type=int, default=3, help="Number of records to retrieve.")
    parser.add_argument(
        "--source",
        choices=["sample", "pubmed"],
        default="sample",
        help="Evidence source. PubMed mode uses public title/abstract metadata.",
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=default_corpus_path(),
        help="Path to a JSONL corpus.",
    )
    parser.add_argument(
        "--retriever",
        choices=["concept", "lexical", "embedding"],
        default="concept",
        help=(
            "Retriever for the local corpus. 'concept' adds ontology grounding "
            "to lexical TF-IDF; 'embedding' needs the optional 'semantic' extra."
        ),
    )
    parser.add_argument(
        "--extractor",
        choices=["deterministic", "llm", "mock-llm"],
        default="deterministic",
        help=(
            "Claim extractor. 'llm' uses a model-backed, citation-grounded "
            "extractor (needs the 'llm' extra + ANTHROPIC_API_KEY); 'mock-llm' "
            "runs the same pipeline with an offline stand-in responder."
        ),
    )
    parser.add_argument(
        "--report",
        choices=["evidence-card", "claim-audit"],
        default="evidence-card",
        help=(
            "Output format. 'claim-audit' renders the BioClaim Auditor report "
            "(verdict, evidence map, citation/overclaim/contradiction audit, "
            "reviewer critique, what-would-change-my-mind)."
        ),
    )
    parser.add_argument(
        "--reviewer",
        choices=["none", "mock", "claude"],
        default="none",
        help=(
            "Reviewer agent that critiques the card (claim-audit report only). "
            "'mock' is offline; 'claude' needs the 'llm' extra + ANTHROPIC_API_KEY."
        ),
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the claim-audit report as JSON instead of Markdown.",
    )
    args = parser.parse_args()

    if args.target:
        from .dossier import DossierError, build_target_dossier, render_dossier

        records = load_corpus(args.corpus)
        try:
            dossier = build_target_dossier(args.target, records)
        except DossierError as exc:
            raise SystemExit(str(exc)) from exc
        print(render_dossier(dossier))
        return

    query = args.claim or args.query
    if args.source == "pubmed":
        try:
            records = search_pubmed(query, top_k=args.top_k)
        except PubMedError as exc:
            raise SystemExit(str(exc)) from exc
        retrieved = [
            RetrievedRecord(record=record, score=1.0 - (index * 0.05))
            for index, record in enumerate(records)
        ]
    else:
        records = load_corpus(args.corpus)
        retrieved = _build_retriever(args.retriever, records).search(
            query, top_k=args.top_k
        )

    card = build_evidence_card(
        query=query,
        retrieved=retrieved,
        claim=args.claim,
        source=args.source,
        extractor=_build_extractor(args.extractor),
    )

    if args.report == "claim-audit":
        from .audit import audit_card
        from .report import audit_json, render_claim_audit
        from .reviewer import review_card

        audit = audit_card(card)
        reviewer = _build_reviewer(args.reviewer)
        critique = review_card(card, audit, reviewer=reviewer) if reviewer else None
        if args.json:
            print(json.dumps(audit_json(card, audit, critique), indent=2))
        else:
            print(render_claim_audit(card, audit, critique))
        return

    print(render_markdown(card))


if __name__ == "__main__":
    main()
