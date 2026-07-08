from __future__ import annotations

import unittest
from pathlib import Path

from biomedical_evidence_agent.audit import (
    audit_card,
    claim_concept_coverage,
    what_would_change_my_mind,
)
from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.report import (
    audit_json,
    evidence_map_html,
    render_claim_audit,
)
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus
from biomedical_evidence_agent.reviewer import mock_reviewer, review_card
from biomedical_evidence_agent.schemas import (
    CorpusRecord,
    EvidenceCard,
    EvidenceClaim,
    RetrievedRecord,
    Verdict,
)

ROOT = Path(__file__).resolve().parents[1]


class AuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cls.retriever = ConceptAwareRetriever(cls.records)

    def _card(self, claim: str) -> EvidenceCard:
        return build_evidence_card(
            query=claim,
            retrieved=self.retriever.search(claim, top_k=5),
            claim=claim,
        )

    def test_contradiction_flag_on_contested_claim(self) -> None:
        audit = audit_card(
            self._card(
                "BRAF V600E melanoma is associated with response to targeted "
                "inhibitor treatment."
            )
        )
        categories = {f.category for f in audit.findings}
        self.assertIn("contradiction", categories)

    def test_overclaim_flag_when_language_outruns_verdict(self) -> None:
        audit = audit_card(
            self._card("TP53 mutation definitively cures colorectal cancer with salbutamol.")
        )
        overclaims = [f for f in audit.findings if f.category == "overclaim"]
        self.assertTrue(overclaims)
        self.assertEqual(overclaims[0].severity, "high")

    def test_well_supported_claim_raises_no_high_flags(self) -> None:
        audit = audit_card(
            self._card("EGFR variants are associated with response to TKI in NSCLC.")
        )
        self.assertFalse([f for f in audit.findings if f.severity == "high"])

    def test_citation_audit_counts_verbatim_quotes(self) -> None:
        audit = audit_card(
            self._card(
                "BRAF V600E melanoma is associated with response to targeted "
                "inhibitor treatment."
            )
        )
        # Deterministic extractor quotes verbatim spans, so all must be faithful.
        self.assertEqual(audit.citations_verbatim, audit.citations_checked)
        self.assertEqual(audit.citation_faithfulness, 1.0)

    def test_non_verbatim_quote_is_flagged(self) -> None:
        # A claim whose quote is NOT a span of its source must fail the citation audit.
        record = CorpusRecord(
            id="s1",
            title="t",
            year=2020,
            entities={},
            abstract="The drug reduced tumor size in the cohort.",
            evidence_type="therapeutic",
            study_design="clinical",
        )
        card = EvidenceCard(
            query="q",
            retrieved=[RetrievedRecord(record=record, score=1.0)],
            claims=[
                EvidenceClaim(
                    text="The drug cured every patient.",  # not in the abstract
                    source_id="s1",
                    evidence_type="therapeutic",
                    confidence="high",
                    stance="supports",
                    tier="clinical",
                )
            ],
            verdict=Verdict(
                label="well-supported",
                strength=1.0,
                support_sources=1,
                conflict_sources=0,
                indirect_sentences=0,
                rationale="x",
            ),
        )
        audit = audit_card(card)
        self.assertEqual(audit.citations_verbatim, 0)
        self.assertTrue([f for f in audit.findings if f.category == "citation"])

    def test_what_would_change_my_mind_is_verdict_specific(self) -> None:
        card = self._card("EGFR variants are associated with response to TKI in NSCLC.")
        wwcmm = what_would_change_my_mind(card, audit_card(card))
        self.assertTrue(any("contradicting" in item for item in wwcmm))

    def test_what_would_change_my_mind_names_claim_entities(self) -> None:
        # A contested claim's next step should name the actual entities at issue.
        card = self._card(
            "TREM2 is associated with Alzheimer's disease progression."
        )
        wwcmm = what_would_change_my_mind(card, audit_card(card))
        joined = " ".join(wwcmm)
        self.assertIn("TREM2", joined)
        self.assertIn("Alzheimer's disease", joined)

    def test_evidence_map_covers_each_claim_entity(self) -> None:
        card = self._card(
            "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
        )
        coverage = {e["name"]: e for e in claim_concept_coverage(card)}
        # BRAF and melanoma are both covered by a supporting and a conflicting source.
        self.assertEqual(coverage["BRAF"]["supports"], 1)
        self.assertEqual(coverage["BRAF"]["conflicts"], 1)
        self.assertIn("melanoma", coverage)

    def test_uncovered_claim_entity_raises_a_coverage_gap(self) -> None:
        # The claim names colorectal cancer, but no retrieved sentence addresses it.
        card = self._card(
            "TP53 mutation definitively cures colorectal cancer with salbutamol."
        )
        audit = audit_card(card)
        gap_messages = [
            f.message for f in audit.findings if f.category == "retrieval-gap"
        ]
        self.assertTrue(any("colorectal cancer" in m for m in gap_messages))


class ReviewerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cls.retriever = ConceptAwareRetriever(cls.records)

    def _card(self, claim: str) -> EvidenceCard:
        return build_evidence_card(
            query=claim, retrieved=self.retriever.search(claim, top_k=5), claim=claim
        )

    def test_mock_reviewer_produces_grounded_critique(self) -> None:
        card = self._card(
            "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
        )
        audit = audit_card(card)
        critique = review_card(card, audit, reviewer=mock_reviewer())
        self.assertTrue(critique.findings)
        self.assertEqual(critique.reviewer, "mock")

    def test_reviewer_drops_a_hallucinated_quote(self) -> None:
        card = self._card("EGFR variants are associated with response to TKI in NSCLC.")
        audit = audit_card(card)

        def bad_reviewer(card, audit):
            return {
                "assessment": "x",
                "findings": [
                    {
                        "kind": "weak-citation",
                        "note": "cites a fabricated quote",
                        "source_id": card.retrieved[0].record.id,
                        "quote": "this text is not in any abstract at all",
                    }
                ],
            }

        critique = review_card(card, audit, reviewer=bad_reviewer)
        # Note is kept, but the unfaithful quote is dropped.
        self.assertEqual(len(critique.findings), 1)
        self.assertEqual(critique.findings[0].quote, "")


class ReportTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cls.retriever = ConceptAwareRetriever(cls.records)

    def _card(self, claim: str) -> EvidenceCard:
        return build_evidence_card(
            query=claim, retrieved=self.retriever.search(claim, top_k=5), claim=claim
        )

    def test_markdown_report_has_audit_sections(self) -> None:
        card = self._card(
            "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
        )
        audit = audit_card(card)
        critique = review_card(card, audit, reviewer=mock_reviewer())
        text = render_claim_audit(card, audit, critique)
        for heading in [
            "# Claim Audit Report",
            "## Audit Verdict",
            "## Evidence Map",
            "## Citation Audit",
            "## What Would Change My Mind?",
            "## Reviewer Critique",
        ]:
            self.assertIn(heading, text)

    def test_evidence_map_html_renders_bars_and_uncovered(self) -> None:
        # A contested claim: each entity gets a supporting + conflicting segment.
        html = evidence_map_html(
            self._card(
                "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
            )
        )
        self.assertIn("em-wrap", html)
        self.assertIn("BRAF", html)
        self.assertIn("#0ca30c", html)  # supporting colour present
        # An uncovered entity renders the red "no evidence" bar.
        overclaim = evidence_map_html(
            self._card("TP53 mutation definitively cures colorectal cancer with salbutamol.")
        )
        self.assertIn("no evidence", overclaim)
        self.assertIn("#d03b3b", overclaim)

    def test_evidence_map_html_is_empty_when_no_entities(self) -> None:
        # A claim with no resolvable entities yields no map (empty string, not markup).
        card = EvidenceCard(query="nothing here", retrieved=[], claims=[], claim="nothing here")
        self.assertEqual(evidence_map_html(card), "")

    def test_json_report_is_serializable_and_complete(self) -> None:
        import json

        card = self._card(
            "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
        )
        audit = audit_card(card)
        payload = audit_json(card, audit, review_card(card, audit, reviewer=mock_reviewer()))
        # Round-trips through JSON and carries the audit essentials.
        restored = json.loads(json.dumps(payload))
        self.assertEqual(restored["verdict"]["label"], "contested")
        self.assertEqual(restored["citation_audit"]["faithfulness"], 1.0)
        self.assertTrue(restored["what_would_change_my_mind"])


if __name__ == "__main__":
    unittest.main()
