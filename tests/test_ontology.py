from __future__ import annotations

import unittest
import unittest.mock
from pathlib import Path

from biomedical_evidence_agent.evaluation import (
    evaluate_entity_linking,
    evaluate_quant,
    evaluate_stance,
    load_entity_cases,
    load_quant_cases,
    load_retrieval_cases,
    load_stance_cases,
    retrieval_ablation,
)
from biomedical_evidence_agent.ontology import Ontology
from biomedical_evidence_agent.quant import extract_measurements
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus

ROOT = Path(__file__).resolve().parents[1]


class OntologyTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ontology = Ontology.load(ROOT / "data" / "ontology.jsonl")

    def test_abbreviation_and_synonym_resolve_to_same_concept(self) -> None:
        for surface in ("EGFR", "ERBB1", "epidermal growth factor receptor"):
            self.assertIn("BEA:gene:egfr", self.ontology.concept_ids(surface))

    def test_brand_alias_resolves_to_generic_drug(self) -> None:
        self.assertIn("BEA:drug:osimertinib", self.ontology.concept_ids("AZD9291"))

    def test_longest_match_wins_over_shorter_overlap(self) -> None:
        # "EGFR inhibitor" must resolve to the drug class, not the bare gene.
        ids = self.ontology.concept_ids("treated with an EGFR inhibitor")
        self.assertIn("BEA:drug_class:egfr_inhibitor", ids)
        self.assertNotIn("BEA:gene:egfr", ids)

    def test_multiword_disease_is_a_single_span(self) -> None:
        matches = self.ontology.normalize("non-small cell lung cancer")
        self.assertEqual(len(matches), 1)
        self.assertEqual(matches[0].concept.id, "BEA:disease:nsclc")

    def test_hyphen_boundary_prevents_partial_match(self) -> None:
        # "EGFR" embedded in "EGFR-mutant" should not link the bare gene here.
        self.assertNotIn("BEA:gene:egfr", self.ontology.concept_ids("EGFR-mutant"))

    def test_generalizes_beyond_oncology(self) -> None:
        ids = self.ontology.concept_ids("salbutamol targets the beta-2 adrenergic receptor")
        self.assertIn("BEA:drug:salbutamol", ids)
        self.assertIn("BEA:gene:adrb2", ids)

    def test_concept_carries_external_xrefs(self) -> None:
        egfr = self.ontology.concepts["BEA:gene:egfr"]
        self.assertEqual(egfr.xrefs["uniprot"], "P00533")

    def test_entity_linking_evaluation_is_accurate_on_gold(self) -> None:
        cases = load_entity_cases(ROOT / "data" / "evaluation_entities.jsonl")
        report = evaluate_entity_linking(self.ontology, cases)
        self.assertEqual(report.false_positives, 0)
        self.assertEqual(report.false_negatives, 0)
        self.assertEqual(report.f1, 1.0)


class HybridRetrievalTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")

    def test_brand_name_query_retrieves_via_concept_grounding(self) -> None:
        # "Tagrisso" appears in neither the corpus nor the alias map; only
        # concept normalization (Tagrisso -> osimertinib) can bridge it.
        results = ConceptAwareRetriever(self.records).search("Tagrisso", top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0].record.id, "toy-001")

    def test_concept_layer_beats_lexical_on_ablation(self) -> None:
        cases = load_retrieval_cases(ROOT / "data" / "evaluation_claims.jsonl")
        lexical, concept = retrieval_ablation(self.records, cases, k=3)
        self.assertEqual(lexical.label, "lexical")
        self.assertEqual(concept.label, "+concept")
        self.assertGreater(concept.recall_at_k, lexical.recall_at_k)


class EmbeddingBackendTest(unittest.TestCase):
    def test_missing_backend_raises_clear_error(self) -> None:
        import builtins

        from biomedical_evidence_agent.embedding import (
            EmbeddingRetriever,
            EmbeddingUnavailable,
        )

        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name.startswith("sentence_transformers"):
                raise ImportError("blocked for test")
            return real_import(name, *args, **kwargs)

        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        with unittest.mock.patch("builtins.__import__", side_effect=blocked_import):
            with self.assertRaises(EmbeddingUnavailable) as ctx:
                EmbeddingRetriever(records)
        self.assertIn("semantic", str(ctx.exception))


class StanceEvaluationTest(unittest.TestCase):
    def test_stance_gold_is_labeled_correctly_with_no_guardrail_leaks(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cases = load_stance_cases(ROOT / "data" / "evaluation_stances.jsonl")
        report = evaluate_stance(records, cases)
        self.assertEqual(report.macro_f1, 1.0)
        self.assertEqual(report.unmatched, 0)
        # Cross-entity and opposite-polarity sentences must never leak through
        # as supporting or conflicting evidence.
        self.assertGreater(report.guardrail_items, 0)
        self.assertEqual(report.guardrail_violations, 0)


class QuantExtractionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ontology = Ontology.load(ROOT / "data" / "ontology.jsonl")

    def test_potency_values_are_attributed_to_the_right_compound(self) -> None:
        text = (
            "Osimertinib inhibited EGFR with an IC50 of 12 nM, whereas gefitinib "
            "inhibited the same target with an IC50 of 38 nM."
        )
        measurements = extract_measurements(text, source_id="x", ontology=self.ontology)
        by_entity = {(m.primary_entity, m.parameter): m.value for m in measurements}
        self.assertEqual(by_entity[("osimertinib", "IC50")], 12.0)
        self.assertEqual(by_entity[("gefitinib", "IC50")], 38.0)

    def test_units_and_relations_are_captured(self) -> None:
        text = "The compound showed a Ki < 0.5 µM and a half-life of 6 h."
        found = {
            (m.parameter, m.relation, m.value, m.unit)
            for m in extract_measurements(text, ontology=self.ontology)
        }
        self.assertIn(("Ki", "<", 0.5, "µM"), found)
        self.assertIn(("half-life", "=", 6.0, "h"), found)

    def test_bare_numbers_are_not_extracted(self) -> None:
        text = "The cohort included 45 patients followed over 12 months."
        self.assertEqual(extract_measurements(text, ontology=self.ontology), [])

    def test_quant_evaluation_is_accurate_on_gold(self) -> None:
        report = evaluate_quant(
            load_quant_cases(ROOT / "data" / "evaluation_quant.jsonl"),
            ontology=self.ontology,
        )
        self.assertEqual(report.false_positives, 0)
        self.assertEqual(report.false_negatives, 0)
        self.assertEqual(report.f1, 1.0)


if __name__ == "__main__":
    unittest.main()
