from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

from .evidence import build_evidence_card
from .retrieval import LexicalRetriever, load_corpus, tokenize
from .schemas import CorpusRecord


@dataclass
class ItemResult:
    query: str
    retrieval_hit: float
    term_coverage: float
    stance_recall: float | None


def default_corpus_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "sample_corpus.jsonl"


def default_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_claims.jsonl"


def load_eval(path: Path) -> list[dict]:
    items: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                items.append(json.loads(line))
    return items


def evaluate(
    records: list[CorpusRecord],
    eval_items: list[dict],
    *,
    top_k: int = 4,
) -> list[ItemResult]:
    retriever = LexicalRetriever(records)
    results: list[ItemResult] = []
    for item in eval_items:
        query = item.get("claim") or item["query"]
        retrieved = retriever.search(query, top_k=top_k)
        card = build_evidence_card(
            query=query,
            retrieved=retrieved,
            claim=item.get("claim"),
        )
        results.append(
            ItemResult(
                query=query,
                retrieval_hit=_retrieval_hit(item, retrieved),
                term_coverage=_term_coverage(item, retrieved),
                stance_recall=_stance_recall(item, card.claims),
            )
        )
    return results


def _retrieval_hit(item: dict, retrieved) -> float:
    expected = item.get("expected_ids") or []
    if not expected:
        return 1.0
    found = {result.record.id for result in retrieved}
    return sum(1 for identifier in expected if identifier in found) / len(expected)


def _term_coverage(item: dict, retrieved) -> float:
    expected_terms = item.get("expected_terms") or []
    if not expected_terms:
        return 1.0
    corpus_tokens: set[str] = set()
    for result in retrieved:
        corpus_tokens.update(tokenize(result.record.title))
        corpus_tokens.update(tokenize(result.record.abstract))
    covered = sum(
        1
        for term in expected_terms
        if set(tokenize(term)) <= corpus_tokens
    )
    return covered / len(expected_terms)


def _stance_recall(item: dict, claims) -> float | None:
    expected_support = set(item.get("expected_supporting_ids") or [])
    expected_conflict = set(item.get("expected_conflicting_ids") or [])
    expects_no_support = item.get("expected_no_support")
    if not expected_support and not expected_conflict and expects_no_support is None:
        return None

    predicted_support = {c.source_id for c in claims if c.stance == "supports"}
    predicted_conflict = {c.source_id for c in claims if c.stance == "conflicts"}

    hits = 0
    total = 0
    for identifier in expected_support:
        total += 1
        hits += identifier in predicted_support
    for identifier in expected_conflict:
        total += 1
        hits += identifier in predicted_conflict
    if expects_no_support is not None:
        total += 1
        hits += bool(expects_no_support) == (not predicted_support)
    return hits / total if total else None


def render_report(results: list[ItemResult]) -> str:
    lines = ["# Evaluation Report", ""]
    for result in results:
        stance = (
            "n/a" if result.stance_recall is None else f"{result.stance_recall:.2f}"
        )
        lines.append(
            f"- retrieval={result.retrieval_hit:.2f} "
            f"terms={result.term_coverage:.2f} stance={stance} :: {result.query}"
        )
    lines.extend(["", "## Aggregate"])
    lines.append(f"- mean retrieval hit@k: {_mean(r.retrieval_hit for r in results):.3f}")
    lines.append(f"- mean term coverage: {_mean(r.term_coverage for r in results):.3f}")
    stance_values = [r.stance_recall for r in results if r.stance_recall is not None]
    if stance_values:
        lines.append(f"- mean stance recall: {_mean(stance_values):.3f}")
    return "\n".join(lines)


def _mean(values) -> float:
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate retrieval and evidence attribution.")
    parser.add_argument("--corpus", type=Path, default=default_corpus_path())
    parser.add_argument("--eval", type=Path, default=default_eval_path())
    parser.add_argument("--top-k", type=int, default=4)
    args = parser.parse_args()

    records = load_corpus(args.corpus)
    eval_items = load_eval(args.eval)
    results = evaluate(records, eval_items, top_k=args.top_k)
    print(render_report(results))


if __name__ == "__main__":
    main()
