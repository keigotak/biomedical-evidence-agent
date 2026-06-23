from __future__ import annotations

import unittest
from pathlib import Path

from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.retrieval import LexicalRetriever, load_corpus


ROOT = Path(__file__).resolve().parents[1]


class PipelineTest(unittest.TestCase):
    def test_retrieves_expected_egfr_record(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        results = LexicalRetriever(records).search(
            "EGFR non-small cell lung cancer tyrosine kinase inhibitor resistance",
            top_k=2,
        )
        self.assertGreaterEqual(len(results), 1)
        self.assertEqual(results[0].record.id, "toy-001")

    def test_builds_evidence_card_with_claims(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        results = LexicalRetriever(records).search("BRAF melanoma targeted therapy", top_k=2)
        card = build_evidence_card("BRAF melanoma targeted therapy", results)
        self.assertEqual(card.query, "BRAF melanoma targeted therapy")
        self.assertTrue(card.retrieved)
        self.assertTrue(card.claims)
        self.assertEqual(card.retrieved[0].record.id, "toy-002")


if __name__ == "__main__":
    unittest.main()
