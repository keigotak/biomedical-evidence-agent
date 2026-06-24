from __future__ import annotations

import unittest
from pathlib import Path

from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.pubmed import _efetch
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

    def test_claim_mode_separates_supporting_and_conflicting_evidence(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        claim = "BRAF melanoma is associated with response to targeted inhibitor treatment."
        results = LexicalRetriever(records).search(claim, top_k=4)
        card = build_evidence_card(query=claim, retrieved=results, claim=claim)
        stances = {claim.stance for claim in card.claims}

        self.assertIn("supports", stances)
        self.assertIn("conflicts", stances)
        self.assertEqual(card.claim, claim)

    def test_low_relevance_conflict_cues_are_insufficient(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        claim = (
            "EGFR activating variants are associated with response to tyrosine kinase "
            "inhibitors in non-small cell lung cancer."
        )
        results = LexicalRetriever(records).search(claim, top_k=3)
        card = build_evidence_card(query=claim, retrieved=results, claim=claim)

        low_relevance_braf_claims = [
            item for item in card.claims if item.source_id == "toy-006"
        ]
        self.assertTrue(low_relevance_braf_claims)
        self.assertTrue(
            all(item.stance == "insufficient" for item in low_relevance_braf_claims)
        )

    def test_pubmed_xml_records_are_mapped_to_corpus_records(self) -> None:
        xml = """<?xml version="1.0" ?>
        <PubmedArticleSet>
          <PubmedArticle>
            <MedlineCitation>
              <PMID>12345</PMID>
              <Article>
                <ArticleTitle>Example biomedical title</ArticleTitle>
                <Journal><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal>
                <Abstract><AbstractText>Example abstract text.</AbstractText></Abstract>
              </Article>
            </MedlineCitation>
          </PubmedArticle>
        </PubmedArticleSet>
        """

        from unittest.mock import patch

        with patch("biomedical_evidence_agent.pubmed._get", return_value=xml):
            records = _efetch(["12345"])

        self.assertEqual(records[0].id, "pubmed-12345")
        self.assertEqual(records[0].year, 2024)
        self.assertEqual(records[0].evidence_type, "public_literature")


if __name__ == "__main__":
    unittest.main()
