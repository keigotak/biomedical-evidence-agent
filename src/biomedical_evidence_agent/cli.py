from __future__ import annotations

import argparse
from pathlib import Path

from .evidence import build_evidence_card, render_markdown
from .retrieval import LexicalRetriever, load_corpus


def default_corpus_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "sample_corpus.jsonl"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a toy biomedical evidence card.")
    parser.add_argument("--query", required=True, help="Biomedical evidence question or topic.")
    parser.add_argument("--top-k", type=int, default=3, help="Number of records to retrieve.")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=default_corpus_path(),
        help="Path to a JSONL corpus.",
    )
    args = parser.parse_args()

    records = load_corpus(args.corpus)
    retrieved = LexicalRetriever(records).search(args.query, top_k=args.top_k)
    card = build_evidence_card(args.query, retrieved)
    print(render_markdown(card))


if __name__ == "__main__":
    main()
