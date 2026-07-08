from __future__ import annotations

import unittest
import unittest.mock
from pathlib import Path

from biomedical_evidence_agent.evaluation import (
    evaluate_entity_linking,
    evaluate_dossier_verdicts,
    evaluate_moa,
    evaluate_quant,
    evaluate_stance,
    evaluate_verdicts,
    load_dossier_cases,
    load_entity_cases,
    load_moa_cases,
    load_quant_cases,
    load_retrieval_cases,
    load_stance_cases,
    load_verdict_cases,
    retrieval_ablation,
)
from biomedical_evidence_agent.evidence import assess_verdict
from biomedical_evidence_agent.ontology import Ontology
from biomedical_evidence_agent.quant import extract_measurements
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus
from biomedical_evidence_agent.schemas import EvidenceClaim

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


class LLMExtractorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cls.ontology = Ontology.load(ROOT / "data" / "ontology.jsonl")

    def _ranked(self, claim: str, k: int = 1):
        return ConceptAwareRetriever(self.records).search(claim, top_k=k)

    def test_faithfulness_guard_drops_hallucinated_quotes(self) -> None:
        from biomedical_evidence_agent.extraction import LLMClaimExtractor

        def responder(claim, record):
            return [
                {"quote": "This sample record describes BRAF V600E melanoma",
                 "stance": "supports", "rationale": "verbatim"},
                {"quote": "BRAF cures melanoma in all patients",
                 "stance": "supports", "rationale": "hallucinated"},
            ]

        ext = LLMClaimExtractor(responder=responder, ontology=self.ontology)
        claims, proposed = ext.extract_with_stats(
            "BRAF melanoma response", self._ranked("BRAF melanoma response")
        )
        self.assertEqual(proposed, 2)
        self.assertEqual(len(claims), 1)
        # Kept claim's span points back to the verbatim source text.
        kept = claims[0]
        self.assertEqual(
            self.records[1].abstract[kept.start:kept.end], kept.text
        )

    def test_grounded_quote_gets_a_valid_span_and_stance(self) -> None:
        from biomedical_evidence_agent.extraction import (
            LLMClaimExtractor,
            heuristic_responder,
        )

        ext = LLMClaimExtractor(
            responder=heuristic_responder(ontology=self.ontology),
            ontology=self.ontology,
        )
        claims = ext.extract(
            "BRAF melanoma is associated with response to targeted inhibitor treatment.",
            self._ranked("BRAF melanoma targeted inhibitor response", k=3),
        )
        self.assertTrue(claims)
        for claim in claims:
            self.assertIn(claim.stance, ("supports", "conflicts", "insufficient"))
            self.assertGreaterEqual(claim.end, claim.start)

    def test_hybrid_guard_demotes_cross_entity_support(self) -> None:
        from biomedical_evidence_agent.extraction import LLMClaimExtractor

        # A BRAF claim; the responder claims an EGFR sentence "supports" it.
        claim = "BRAF is associated with response to targeted therapy."

        def responder(_claim, record):
            if record.id != "toy-001":
                return []
            return [{
                "quote": "In this toy abstract, EGFR activating variants are "
                         "associated with response to tyrosine kinase inhibitors "
                         "in non-small cell lung cancer.",
                "stance": "supports",
                "rationale": "cross-entity: names EGFR, not BRAF",
            }]

        ranked = self._ranked(claim, k=5)
        unguarded = LLMClaimExtractor(
            responder=responder, ontology=self.ontology, guard=False
        ).extract(claim, ranked)
        hybrid = LLMClaimExtractor(
            responder=responder, ontology=self.ontology, guard=True
        ).extract(claim, ranked)
        self.assertEqual([c.stance for c in unguarded], ["supports"])
        # The hybrid guard demotes the cross-entity quote to insufficient.
        self.assertEqual([c.stance for c in hybrid], ["insufficient"])

    def test_missing_backend_raises_clear_error(self) -> None:
        import builtins

        from biomedical_evidence_agent.extraction import (
            ExtractorUnavailable,
            anthropic_responder,
        )

        real_import = builtins.__import__

        def blocked_import(name, *args, **kwargs):
            if name == "anthropic":
                raise ImportError("blocked for test")
            return real_import(name, *args, **kwargs)

        with unittest.mock.patch("builtins.__import__", side_effect=blocked_import):
            with self.assertRaises(ExtractorUnavailable) as ctx:
                anthropic_responder()
        self.assertIn("llm", str(ctx.exception))


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


class TargetDossierTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cls.ontology = Ontology.load(ROOT / "data" / "ontology.jsonl")

    def _dossier(self, target: str):
        from biomedical_evidence_agent.dossier import build_target_dossier

        return build_target_dossier(target, self.records, ontology=self.ontology)

    def test_target_normalizes_from_a_synonym(self) -> None:
        # "ERBB1" is a synonym; the dossier must resolve it to the EGFR concept.
        dossier = self._dossier("ERBB1")
        self.assertEqual(dossier.target_id, "BEA:gene:egfr")
        self.assertIn("toy-007", dossier.record_ids)

    def test_compounds_carry_potencies_and_declared_flag(self) -> None:
        dossier = self._dossier("EGFR")
        by_name = {c.name: c for c in dossier.compounds}
        self.assertTrue(by_name["osimertinib"].declared_target)
        potencies = {
            (m.parameter, m.value) for m in by_name["osimertinib"].measurements
        }
        self.assertIn(("IC50", 12.0), potencies)
        # Generic co-mentioned classes are not listed as modulators.
        self.assertNotIn("targeted therapy", by_name)

    def test_dossier_generalizes_to_non_oncology(self) -> None:
        dossier = self._dossier("beta-2 adrenergic receptor")
        self.assertEqual(dossier.target_id, "BEA:gene:adrb2")
        names = {c.name for c in dossier.compounds}
        self.assertIn("salbutamol", names)
        self.assertIn("inflammatory disease", dossier.diseases)

    def test_unresolvable_target_raises(self) -> None:
        from biomedical_evidence_agent.dossier import DossierError

        with self.assertRaises(DossierError):
            self._dossier("nonexistent frobnicator")

    def test_indication_verdicts_grade_target_validation(self) -> None:
        egfr = self._dossier("EGFR")
        self.assertEqual(
            egfr.indication_verdicts["non-small cell lung cancer"].label,
            "well-supported",
        )
        # BRAF/melanoma has one clinical support and one clinical conflict.
        braf = self._dossier("BRAF")
        self.assertEqual(braf.indication_verdicts["melanoma"].label, "contested")

    def test_modulator_verdict_grades_only_potency_as_insufficient(self) -> None:
        # On the shared corpus every EGFR modulator has potency/declaration but no
        # drug-specific outcome sentence, so validation must stay insufficient.
        egfr = self._dossier("EGFR")
        by_name = {c.name: c for c in egfr.compounds}
        self.assertEqual(by_name["osimertinib"].verdict.label, "insufficient")

    def test_modulator_verdict_is_drug_grounded_no_cross_entity_leak(self) -> None:
        from biomedical_evidence_agent.dossier import build_target_dossier
        from biomedical_evidence_agent.schemas import CorpusRecord

        def record(rid: str, abstract: str, design: str = "clinical") -> CorpusRecord:
            return CorpusRecord(
                id=rid,
                title=rid,
                year=2022,
                entities={"genes": ["EGFR"], "diseases": ["non-small cell lung cancer"]},
                abstract=abstract,
                evidence_type="therapeutic",
                study_design=design,
            )

        records = [
            # Target-level outcome evidence naming EGFR but NO specific drug — the leak bait.
            record(
                "r-egfr",
                "EGFR activating variants are associated with response to tyrosine "
                "kinase inhibitors in non-small cell lung cancer.",
            ),
            # Drug-specific outcome evidence naming osimertinib.
            record(
                "r-osi",
                "Osimertinib was associated with durable clinical response in "
                "non-small cell lung cancer.",
            ),
            # Gefitinib appears only with potency, never in an outcome sentence.
            record(
                "r-gef",
                "In a synthetic in vitro assay gefitinib inhibited the target with "
                "an IC50 of 38 nM.",
                design="in_vitro",
            ),
        ]
        dossier = build_target_dossier("EGFR", records, ontology=self.ontology)
        by_name = {c.name: c for c in dossier.compounds}
        # Osimertinib is validated by its own outcome sentence.
        self.assertEqual(by_name["osimertinib"].verdict.label, "well-supported")
        # Gefitinib must NOT inherit the EGFR-level support: no drug-grounded outcome.
        self.assertEqual(by_name["gefitinib"].verdict.label, "insufficient")

    def test_dossier_rolls_up_modulator_mechanism(self) -> None:
        egfr = {c.name: c for c in self._dossier("EGFR").compounds}
        self.assertEqual(egfr["osimertinib"].mechanism, "antagonist")
        # Non-oncology: an agonist is labeled from the same grounded extractor.
        adrb2 = {c.name: c for c in self._dossier("beta-2 adrenergic receptor").compounds}
        self.assertEqual(adrb2["salbutamol"].mechanism, "agonist")


class MoaExtractionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ontology = Ontology.load(ROOT / "data" / "ontology.jsonl")

    def _extract(self, text: str):
        from biomedical_evidence_agent.moa import extract_moa

        return extract_moa(text, ontology=self.ontology)

    def test_inhibition_is_an_antagonist_relation(self) -> None:
        rels = self._extract("Osimertinib inhibited mutant EGFR in the assay.")
        self.assertEqual(len(rels), 1)
        self.assertEqual(
            (rels[0].drug_name, rels[0].target_name, rels[0].mechanism),
            ("osimertinib", "EGFR", "antagonist"),
        )

    def test_activation_is_an_agonist_relation(self) -> None:
        rels = self._extract("Salbutamol activated the beta-2 adrenergic receptor.")
        self.assertEqual(
            [(r.drug_name, r.mechanism) for r in rels], [("salbutamol", "agonist")]
        )

    def test_activated_gene_without_a_drug_yields_nothing(self) -> None:
        # "EGFR activating variants" is the gene being activated, not a drug MoA.
        self.assertEqual(self._extract("EGFR activating variants drive tumor growth."), [])

    def test_drug_is_not_paired_with_a_non_target_gene(self) -> None:
        # BRAF is present and a cue fires, but osimertinib does not target BRAF.
        rels = self._extract("Osimertinib was tested while BRAF signaling was inhibited.")
        self.assertEqual([(r.drug_name, r.target_name) for r in rels], [])

    def test_moa_evaluation_matches_gold(self) -> None:
        report = evaluate_moa(load_moa_cases(ROOT / "data" / "evaluation_moa.jsonl"))
        self.assertEqual(report.f1, 1.0)
        self.assertEqual(report.false_positives, 0)


class VerdictTest(unittest.TestCase):
    @staticmethod
    def _claim(source_id, stance, tier):
        return EvidenceClaim(
            text="x", source_id=source_id, evidence_type="t",
            confidence="medium", stance=stance, tier=tier,
        )

    def test_a_strong_conflict_outweighs_many_weak_supports(self) -> None:
        # Three in_silico supporting sentences from ONE source vs one clinical
        # conflict: source-level, tier-weighted counting must not let the volume win.
        claims = [
            self._claim("s1", "supports", "in_silico"),
            self._claim("s1", "supports", "in_silico"),
            self._claim("s1", "supports", "in_silico"),
            self._claim("c1", "conflicts", "clinical"),
        ]
        verdict = assess_verdict(claims)
        # One in_silico source (0.4) vs one clinical source (1.0): net leans against.
        self.assertEqual(verdict.support_sources, 1)
        self.assertLess(verdict.strength, 0)

    def test_balanced_clinical_evidence_is_contested(self) -> None:
        verdict = assess_verdict([
            self._claim("s1", "supports", "clinical"),
            self._claim("c1", "conflicts", "clinical"),
        ])
        self.assertEqual(verdict.label, "contested")

    def test_clean_support_is_well_supported(self) -> None:
        verdict = assess_verdict([self._claim("s1", "supports", "clinical")])
        self.assertEqual(verdict.label, "well-supported")
        self.assertEqual(verdict.strength, 1.0)

    def test_in_silico_only_is_insufficient(self) -> None:
        verdict = assess_verdict([self._claim("s1", "supports", "in_silico")])
        self.assertEqual(verdict.label, "insufficient")

    def test_no_on_claim_evidence_is_insufficient(self) -> None:
        verdict = assess_verdict([self._claim("s1", "insufficient", "clinical")])
        self.assertEqual(verdict.label, "insufficient")
        self.assertEqual(verdict.indirect_sentences, 1)

    def test_verdict_evaluation_matches_gold(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cases = load_verdict_cases(ROOT / "data" / "evaluation_verdicts.jsonl")
        report = evaluate_verdicts(records, cases)
        self.assertEqual(report.accuracy, 1.0)

    def test_dossier_indication_verdict_evaluation_matches_gold(self) -> None:
        records = load_corpus(ROOT / "data" / "sample_corpus.jsonl")
        cases = load_dossier_cases(ROOT / "data" / "evaluation_dossiers.jsonl")
        # Gold spans all three verdict labels incl. a non-oncology control.
        self.assertEqual(len({c.expected_label for c in cases}), 3)
        report = evaluate_dossier_verdicts(records, cases)
        self.assertEqual(report.accuracy, 1.0)


if __name__ == "__main__":
    unittest.main()
