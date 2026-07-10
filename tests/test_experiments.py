from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "experiments"))

import compare_claims  # noqa: E402
import document_audit  # noqa: E402
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


class CompareClaimsTest(unittest.TestCase):
    CORPUS = ROOT / "data" / "sample_corpus.jsonl"

    def test_table_grades_each_claim(self) -> None:
        table = compare_claims.compare(
            [
                "EGFR variants are associated with response to TKI in NSCLC.",
                "TP53 mutation definitively cures colorectal cancer with salbutamol.",
            ],
            corpus=self.CORPUS,
        )
        self.assertIn("| Claim | Verdict |", table)
        # Bind each verdict to ITS OWN row, not just "appears somewhere in the table".
        rows = {
            line.split("|")[1].strip(): line
            for line in table.splitlines()
            if line.startswith("| ") and "Verdict" not in line and "---" not in line
        }
        egfr = next(v for k, v in rows.items() if k.startswith("EGFR"))
        tp53 = next(v for k, v in rows.items() if k.startswith("TP53"))
        self.assertIn("well-supported", egfr)
        self.assertNotIn("well-supported", tp53)
        self.assertIn("overclaim", tp53)


class DocumentAuditTest(unittest.TestCase):
    CORPUS = ROOT / "data" / "sample_corpus.jsonl"

    def test_only_concept_bearing_assertions_become_claims(self) -> None:
        from biomedical_evidence_agent.ontology import Ontology

        passage = (
            "BRAF V600E melanoma is associated with response to targeted inhibitor "
            "treatment. The assay was run in triplicate at room temperature. "
            "EGFR is a receptor tyrosine kinase."
        )
        claims = document_audit.extract_claims(passage, Ontology.load())
        # The methods sentence (no concept, no cue) and the bare definition (concept
        # but no assertion cue) are both excluded; only the real claim survives.
        self.assertEqual(len(claims), 1)
        self.assertIn("BRAF", claims[0])

    def test_batch_report_flags_the_overclaim(self) -> None:
        passage = (
            "EGFR variants are associated with response to TKI in NSCLC. "
            "TP53 mutation definitively cures colorectal cancer with salbutamol."
        )
        result = document_audit.audit_document(passage, corpus=self.CORPUS)
        self.assertEqual(result["claims_found"], 2)
        report = document_audit.render_document_audit(result)
        self.assertIn("well-supported", report)
        self.assertIn("overclaim", report)


if __name__ == "__main__":
    unittest.main()
