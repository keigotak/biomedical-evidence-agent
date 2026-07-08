from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import reviewer_duel  # noqa: E402


class ReviewerDuelTest(unittest.TestCase):
    CORPUS = ROOT / "data" / "sample_corpus.jsonl"

    def test_contested_claim_is_a_draw(self) -> None:
        result = reviewer_duel.run_duel(
            "BRAF V600E melanoma is associated with response to targeted inhibitor treatment.",
            corpus=self.CORPUS,
        )
        self.assertEqual(result["ruling"]["winner"], "draw")
        # Both sides cite grounded evidence.
        self.assertTrue(result["advocate"]["points"])
        self.assertTrue(result["skeptic"]["points"])

    def test_unsupported_overclaim_goes_to_the_skeptic(self) -> None:
        result = reviewer_duel.run_duel(
            "TP53 mutation definitively cures colorectal cancer with salbutamol.",
            corpus=self.CORPUS,
        )
        self.assertEqual(result["ruling"]["winner"], "skeptic")

    def test_a_fabricated_quote_is_dropped_from_a_debater(self) -> None:
        def lying_advocate(card, audit):
            return {
                "argument": "trust me",
                "points": [
                    {
                        "note": "cites a fabricated quote",
                        "source_id": card.retrieved[0].record.id,
                        "quote": "this exact sentence appears in no abstract",
                    }
                ],
            }

        result = reviewer_duel.run_duel(
            "BRAF V600E melanoma is associated with response to targeted inhibitor treatment.",
            corpus=self.CORPUS,
            advocate=lying_advocate,
        )
        point = result["advocate"]["points"][0]
        self.assertEqual(point["note"], "cites a fabricated quote")
        self.assertEqual(point["quote"], "")  # unfaithful citation dropped


if __name__ == "__main__":
    unittest.main()
