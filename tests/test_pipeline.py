from __future__ import annotations

import unittest
from pathlib import Path

from biomedical_evidence_agent.evidence import build_evidence_card, render_markdown
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
        # Top hit is one of the BRAF/melanoma records; their relative rank is
        # IDF-sensitive as the corpus grows, so don't pin a single id.
        self.assertIn(card.retrieved[0].record.id, {"toy-002", "toy-006"})

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

    def test_response_sentence_is_not_supporting_a_resistance_claim(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        claim = (
            "EGFR T790M is associated with resistance to first-generation EGFR "
            "inhibitors in non-small cell lung cancer."
        )
        results = LexicalRetriever(records).search(claim, top_k=3)
        card = build_evidence_card(query=claim, retrieved=results, claim=claim)

        # The only strongly retrieved sentence describes response (opposite outcome),
        # so it must not be attributed as supporting a resistance claim.
        supporting = [item for item in card.claims if item.stance == "supports"]
        self.assertFalse(supporting)
        response_claim = next(
            item
            for item in card.claims
            if "associated with response" in item.text
        )
        self.assertEqual(response_claim.stance, "insufficient")

    def test_cross_gene_sentence_is_not_supporting_evidence(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        claim = "EGFR is associated with response to targeted therapy."
        results = LexicalRetriever(records).search(claim, top_k=5)
        card = build_evidence_card(query=claim, retrieved=results, claim=claim)

        # BRAF sentences (toy-002/toy-006) do not name EGFR, so they cannot be
        # grounded to the EGFR claim as supporting or conflicting evidence.
        braf_stances = {
            item.stance
            for item in card.claims
            if item.source_id in {"toy-002", "toy-006"}
        }
        self.assertTrue(braf_stances)
        self.assertNotIn("supports", braf_stances)
        self.assertNotIn("conflicts", braf_stances)

    def test_abbreviation_query_retrieves_full_form_record(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        # The corpus spells "non-small cell lung cancer" and "tyrosine kinase
        # inhibitors" out in full; the query uses abbreviations only.
        results = LexicalRetriever(records).search("TKI response in NSCLC", top_k=2)
        self.assertTrue(results)
        self.assertEqual(results[0].record.id, "toy-001")

    def test_claims_carry_multiple_facets(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        claim = "EGFR variants are associated with response to TKI in NSCLC."
        results = LexicalRetriever(records).search(claim, top_k=3)
        card = build_evidence_card(query=claim, retrieved=results, claim=claim)

        supporting = next(item for item in card.claims if item.stance == "supports")
        self.assertIn("mechanism", supporting.facets)
        self.assertIn("clinical", supporting.facets)
        self.assertGreaterEqual(len(supporting.facets), 2)

        rendered = render_markdown(card)
        self.assertIn("## Evidence by Angle", rendered)

    def test_caps_evidence_sentences_per_source_and_stance(self) -> None:
        from collections import Counter

        from biomedical_evidence_agent.evidence import (
            MAX_SENTENCES_PER_SOURCE_STANCE,
            _cap_per_source,
        )

        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        claim = "BRAF melanoma is associated with response to targeted inhibitor treatment."
        results = LexicalRetriever(records).search(claim, top_k=4)
        card = build_evidence_card(query=claim, retrieved=results, claim=claim)
        # Assert the cap on the structured claims (what the renderer applies), not
        # on a substring count of the rendered markdown.
        for stance in ("supports", "conflicts", "insufficient"):
            group = [c for c in card.claims if c.stance == stance]
            counts = Counter(c.source_id for c in _cap_per_source(group))
            self.assertTrue(
                all(n <= MAX_SENTENCES_PER_SOURCE_STANCE for n in counts.values()),
                f"{stance}: {counts}",
            )

    def test_workflow_claim_can_be_supporting_evidence(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        claim = (
            "Neoantigen prediction can prioritize candidates using HLA typing, "
            "RNA expression, and peptide binding scores."
        )
        results = LexicalRetriever(records).search(claim, top_k=3)
        card = build_evidence_card(query=claim, retrieved=results, claim=claim)

        supporting = [item for item in card.claims if item.stance == "supports"]
        self.assertTrue(supporting)
        self.assertEqual(supporting[0].source_id, "toy-003")

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
