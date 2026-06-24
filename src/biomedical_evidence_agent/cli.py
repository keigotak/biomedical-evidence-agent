from __future__ import annotations

import argparse
from pathlib import Path

from .evidence import build_evidence_card, render_markdown
from .pubmed import PubMedError, search_pubmed
from .retrieval import LexicalRetriever, load_corpus
from .schemas import RetrievedRecord


def default_corpus_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "sample_corpus.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a biomedical evidence card.")
    query_group = parser.add_mutually_exclusive_group(required=True)
    query_group.add_argument("--query", help="Biomedical evidence question or topic.")
    query_group.add_argument("--claim", help="Biomedical claim to review against retrieved evidence.")
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
    args = parser.parse_args()

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
        retrieved = LexicalRetriever(records).search(query, top_k=args.top_k)

    card = build_evidence_card(
        query=query,
        retrieved=retrieved,
        claim=args.claim,
        source=args.source,
    )
    print(render_markdown(card))


if __name__ == "__main__":
    main()
