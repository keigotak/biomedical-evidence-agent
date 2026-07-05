from __future__ import annotations

import argparse
from pathlib import Path

from .evidence import build_evidence_card, render_markdown
from .pubmed import PubMedError, search_pubmed
from .retrieval import ConceptAwareRetriever, LexicalRetriever, load_corpus
from .schemas import RetrievedRecord


def default_corpus_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "sample_corpus.jsonl"


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
    print(render_markdown(card))


if __name__ == "__main__":
    main()
