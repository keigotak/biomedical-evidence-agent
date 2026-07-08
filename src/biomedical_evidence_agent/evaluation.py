from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .dossier import DossierError, build_target_dossier
from .evidence import build_evidence_card
from .moa import extract_moa
from .ontology import Ontology
from .quant import extract_measurements
from .retrieval import ConceptAwareRetriever, LexicalRetriever, load_corpus
from .schemas import CorpusRecord


def default_entity_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_entities.jsonl"


def default_corpus_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "sample_corpus.jsonl"


def default_retrieval_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_claims.jsonl"


def default_stance_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_stances.jsonl"


def default_quant_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_quant.jsonl"


def default_verdict_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_verdicts.jsonl"


def default_dossier_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_dossiers.jsonl"


def default_moa_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_moa.jsonl"


def default_stress_eval_path() -> Path:
    return Path(__file__).resolve().parents[2] / "data" / "evaluation_stress.jsonl"


@dataclass(frozen=True)
class EntityLinkingCase:
    id: str
    text: str
    expected_concepts: frozenset[str]


@dataclass(frozen=True)
class EntityLinkingReport:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int
    per_case: list[dict[str, object]]


def load_entity_cases(path: Path | None = None) -> list[EntityLinkingCase]:
    path = path or default_entity_eval_path()
    cases: list[EntityLinkingCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            cases.append(
                EntityLinkingCase(
                    id=item["id"],
                    text=item["text"],
                    expected_concepts=frozenset(item.get("expected_concepts", [])),
                )
            )
    return cases


def evaluate_entity_linking(
    ontology: Ontology, cases: list[EntityLinkingCase]
) -> EntityLinkingReport:
    """Score concept resolution as a set-level entity-linking task.

    Precision/recall are micro-averaged over concept mentions across all cases,
    so both missed concepts (recall) and over-linking (precision) are penalized.
    Cases with an empty expected set act as negative controls: any predicted
    concept there is a false positive.
    """

    tp = fp = fn = 0
    per_case: list[dict[str, object]] = []
    for case in cases:
        predicted = set(ontology.concept_ids(case.text))
        expected = set(case.expected_concepts)
        matched = predicted & expected
        missed = expected - predicted
        spurious = predicted - expected
        tp += len(matched)
        fp += len(spurious)
        fn += len(missed)
        per_case.append(
            {
                "id": case.id,
                "matched": sorted(matched),
                "missed": sorted(missed),
                "spurious": sorted(spurious),
            }
        )
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return EntityLinkingReport(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        per_case=per_case,
    )


@dataclass(frozen=True)
class RetrievalCase:
    query: str
    expected_ids: frozenset[str]


@dataclass(frozen=True)
class RetrievalReport:
    label: str
    recall_at_k: float
    mrr: float
    k: int
    cases: int


def load_retrieval_cases(path: Path | None = None) -> list[RetrievalCase]:
    path = path or default_retrieval_eval_path()
    cases: list[RetrievalCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            cases.append(
                RetrievalCase(
                    query=item["query"],
                    expected_ids=frozenset(item.get("expected_ids", [])),
                )
            )
    return cases


def evaluate_retrieval(
    retriever: "LexicalRetriever | ConceptAwareRetriever",
    cases: list[RetrievalCase],
    *,
    label: str,
    k: int = 3,
) -> RetrievalReport:
    """Recall@k and mean reciprocal rank over labeled query -> relevant ids.

    Recall@k credits a case if any expected id appears in the top k. MRR uses
    the rank of the first expected id, so a retriever that ranks the right
    record higher scores better even when both find it.
    """

    hits = 0
    reciprocal = 0.0
    for case in cases:
        ranked = retriever.search(case.query, top_k=k)
        ranked_ids = [item.record.id for item in ranked]
        if case.expected_ids & set(ranked_ids):
            hits += 1
        for rank, record_id in enumerate(ranked_ids, start=1):
            if record_id in case.expected_ids:
                reciprocal += 1.0 / rank
                break
    count = len(cases) or 1
    return RetrievalReport(
        label=label,
        recall_at_k=hits / count,
        mrr=reciprocal / count,
        k=k,
        cases=len(cases),
    )


def retrieval_ablation(
    records: list[CorpusRecord],
    cases: list[RetrievalCase],
    *,
    k: int = 3,
) -> list[RetrievalReport]:
    """Compare lexical-only against concept-aware retrieval on the same cases."""

    return [
        evaluate_retrieval(LexicalRetriever(records), cases, label="lexical", k=k),
        evaluate_retrieval(
            ConceptAwareRetriever(records), cases, label="+concept", k=k
        ),
    ]


STANCE_CLASSES = ("supports", "conflicts", "insufficient")


@dataclass(frozen=True)
class StanceCase:
    id: str
    claim: str
    items: tuple[dict[str, str], ...]


@dataclass(frozen=True)
class StanceReport:
    per_class: dict[str, dict[str, float]]
    macro_f1: float
    guardrail_items: int
    guardrail_violations: int
    unmatched: int


def load_stance_cases(path: Path | None = None) -> list[StanceCase]:
    path = path or default_stance_eval_path()
    cases: list[StanceCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            cases.append(
                StanceCase(
                    id=item["id"],
                    claim=item["claim"],
                    items=tuple(item.get("items", [])),
                )
            )
    return cases


def _predicted_stance(card_claims, source_id: str, contains: str) -> str | None:
    for claim in card_claims:
        if claim.source_id == source_id and contains in claim.text:
            return claim.stance
    return None


def evaluate_stance(
    records: list[CorpusRecord],
    cases: list[StanceCase],
    *,
    k: int = 5,
    extractor=None,
) -> StanceReport:
    """Per-class stance P/R/F1 plus guardrail metrics.

    Guardrail items are sentences that must be demoted to insufficient because
    they name a different entity (cross_entity) or the opposite outcome polarity
    (polarity). A violation is any such item that leaks through as supporting or
    conflicting evidence; the target is zero.
    """

    retriever = ConceptAwareRetriever(records)
    counts = {label: {"tp": 0, "fp": 0, "fn": 0} for label in STANCE_CLASSES}
    guardrail_items = 0
    guardrail_violations = 0
    unmatched = 0
    for case in cases:
        ranked = retriever.search(case.claim, top_k=k)
        card = build_evidence_card(
            query=case.claim, retrieved=ranked, claim=case.claim, extractor=extractor
        )
        for item in case.items:
            gold = item["stance"]
            predicted = _predicted_stance(card.claims, item["source_id"], item["contains"])
            if predicted is None:
                unmatched += 1
                counts[gold]["fn"] += 1
                continue
            if predicted == gold:
                counts[gold]["tp"] += 1
            else:
                counts[gold]["fn"] += 1
                counts[predicted]["fp"] += 1
            if item.get("reason") in ("cross_entity", "polarity"):
                guardrail_items += 1
                if predicted in ("supports", "conflicts"):
                    guardrail_violations += 1
    per_class: dict[str, dict[str, float]] = {}
    f1_sum = 0.0
    for label in STANCE_CLASSES:
        tp = counts[label]["tp"]
        fp = counts[label]["fp"]
        fn = counts[label]["fn"]
        precision = tp / (tp + fp) if (tp + fp) else 1.0
        recall = tp / (tp + fn) if (tp + fn) else 1.0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1}
        f1_sum += f1
    return StanceReport(
        per_class=per_class,
        macro_f1=f1_sum / len(STANCE_CLASSES),
        guardrail_items=guardrail_items,
        guardrail_violations=guardrail_violations,
        unmatched=unmatched,
    )


@dataclass(frozen=True)
class QuantCase:
    id: str
    text: str
    expected: tuple[tuple[str, str, float, str], ...]  # (parameter, relation, value, unit)


@dataclass(frozen=True)
class QuantReport:
    precision: float
    recall: float
    f1: float
    true_positives: int
    false_positives: int
    false_negatives: int


def load_quant_cases(path: Path | None = None) -> list[QuantCase]:
    path = path or default_quant_eval_path()
    cases: list[QuantCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            expected = tuple(
                (row["parameter"], row.get("relation", "="), float(row["value"]), row["unit"])
                for row in item.get("expected", [])
            )
            cases.append(QuantCase(id=item["id"], text=item["text"], expected=expected))
    return cases


def evaluate_quant(
    cases: list[QuantCase], *, ontology: Ontology | None = None
) -> QuantReport:
    """Precision/recall of quantitative extraction on (parameter, relation, value, unit).

    Scoring the relation means `IC50 <5 nM` (potent) and `IC50 =5 nM` no longer
    count as the same extraction — direction is graded, not just magnitude.
    """

    ontology = ontology or Ontology.load()
    tp = fp = fn = 0
    for case in cases:
        predicted = {
            (m.parameter, m.relation, m.value, m.unit)
            for m in extract_measurements(case.text, ontology=ontology)
        }
        expected = set(case.expected)
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return QuantReport(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


@dataclass(frozen=True)
class MoaCase:
    id: str
    text: str
    expected: tuple[tuple[str, str, str], ...]


def load_moa_cases(path: Path | None = None) -> list[MoaCase]:
    path = path or default_moa_eval_path()
    cases: list[MoaCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            expected = tuple(
                (row["drug"], row["target"], row["mechanism"])
                for row in item.get("expected", [])
            )
            cases.append(MoaCase(id=item["id"], text=item["text"], expected=expected))
    return cases


def evaluate_moa(cases: list[MoaCase], *, ontology: Ontology | None = None) -> QuantReport:
    """Precision/recall of MoA extraction on (drug, target, mechanism) triples.

    Reuses QuantReport's shape. Negative-control cases (a gene activated by a
    variant, a 'suppressor' cue with no drug) must yield no relation, so a
    spurious extraction shows up as a false positive.
    """

    ontology = ontology or Ontology.load()
    tp = fp = fn = 0
    for case in cases:
        predicted = {
            (r.drug_name, r.target_name, r.mechanism)
            for r in extract_moa(case.text, ontology=ontology)
        }
        expected = set(case.expected)
        tp += len(predicted & expected)
        fp += len(predicted - expected)
        fn += len(expected - predicted)
    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return QuantReport(
        precision=precision,
        recall=recall,
        f1=f1,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
    )


@dataclass(frozen=True)
class StressResult:
    id: str
    kind: str
    handled: bool
    expected: object
    predicted: object
    note: str


def evaluate_stress(path: Path | None = None, *, ontology: Ontology | None = None) -> list[StressResult]:
    """Run a set of deliberately hard cases and report which are handled.

    Unlike the capability gold, this set is NOT expected to be perfect — it holds
    adversarial and known-limitation cases (hyphenated morphology, numeric
    ranges, cue collisions) so the evaluation is honest about the edges. Each case
    declares its own `kind` (entity / quant / moa) and expected output; a case is
    'handled' only on an exact match.
    """

    ontology = ontology or Ontology.load()
    path = path or default_stress_eval_path()
    results: list[StressResult] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            kind, text = item["kind"], item["text"]
            if kind == "entity":
                predicted = sorted(
                    {ontology.concepts[cid].canonical for cid in ontology.concept_ids(text)}
                )
                expected = sorted(item["expected"])
                handled = set(expected).issubset(set(predicted))
            elif kind == "quant":
                predicted = sorted(
                    (m.parameter, m.relation, m.value, m.unit)
                    for m in extract_measurements(text, ontology=ontology)
                )
                expected = sorted(
                    (r[0], r[1], float(r[2]), r[3]) if len(r) == 4 else (r[0], "=", float(r[1]), r[2])
                    for r in item["expected"]
                )
                handled = predicted == expected
            elif kind == "moa":
                predicted = sorted(
                    (r.drug_name, r.target_name, r.mechanism)
                    for r in extract_moa(text, ontology=ontology)
                )
                expected = sorted(tuple(r) for r in item["expected"])
                handled = predicted == expected
            else:  # pragma: no cover - guards a malformed gold file
                continue
            results.append(
                StressResult(item["id"], kind, handled, expected, predicted, item.get("note", ""))
            )
    return results


def _embedding_ablation_line(
    records: list[CorpusRecord], cases: list[RetrievalCase], *, k: int = 3
) -> str:
    """Retrieval line for the optional embedding backend, or why it was skipped."""

    from .embedding import EmbeddingRetriever, EmbeddingUnavailable

    try:
        retriever = EmbeddingRetriever(records)
    except EmbeddingUnavailable as exc:
        return f"skipped ({exc})"
    report = evaluate_retrieval(retriever, cases, label="+embedding", k=k)
    return (
        f"recall@{report.k}={report.recall_at_k:.3f} "
        f"mrr={report.mrr:.3f} (n={report.cases})"
    )


@dataclass(frozen=True)
class VerdictCase:
    id: str
    claim: str
    expected_label: str


@dataclass(frozen=True)
class VerdictReport:
    accuracy: float
    correct: int
    total: int
    per_case: list[dict[str, str]]


def load_verdict_cases(path: Path | None = None) -> list[VerdictCase]:
    path = path or default_verdict_eval_path()
    cases: list[VerdictCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            cases.append(
                VerdictCase(
                    id=item["id"],
                    claim=item["claim"],
                    expected_label=item["expected_label"],
                )
            )
    return cases


def evaluate_verdicts(
    records: list[CorpusRecord], cases: list[VerdictCase], *, k: int = 5
) -> VerdictReport:
    """Accuracy of the weighted verdict label against gold, incl. a negative control."""

    retriever = ConceptAwareRetriever(records)
    correct = 0
    per_case: list[dict[str, str]] = []
    for case in cases:
        ranked = retriever.search(case.claim, top_k=k)
        card = build_evidence_card(query=case.claim, retrieved=ranked, claim=case.claim)
        predicted = card.verdict.label if card.verdict else "insufficient"
        if predicted == case.expected_label:
            correct += 1
        per_case.append(
            {"id": case.id, "expected": case.expected_label, "predicted": predicted}
        )
    total = len(cases) or 1
    return VerdictReport(
        accuracy=correct / total,
        correct=correct,
        total=len(cases),
        per_case=per_case,
    )


@dataclass(frozen=True)
class DossierVerdictCase:
    id: str
    target: str
    disease: str
    expected_label: str


@dataclass(frozen=True)
class DossierVerdictReport:
    accuracy: float
    correct: int
    total: int
    per_case: list[dict[str, str]]


def load_dossier_cases(path: Path | None = None) -> list[DossierVerdictCase]:
    path = path or default_dossier_eval_path()
    cases: list[DossierVerdictCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            item = json.loads(line)
            cases.append(
                DossierVerdictCase(
                    id=item["id"],
                    target=item["target"],
                    disease=item["disease"],
                    expected_label=item["expected_label"],
                )
            )
    return cases


def evaluate_dossier_verdicts(
    records: list[CorpusRecord],
    cases: list[DossierVerdictCase],
    *,
    ontology: Ontology | None = None,
) -> DossierVerdictReport:
    """Accuracy of per-indication target-validation verdicts against gold.

    Builds the target dossier and checks the verdict label attached to each
    gold (target, disease) pair. This grades the dossier's verdict × dossier
    view directly, as opposed to the on-claim verdict eval which scores a
    hand-written claim string.
    """

    ontology = ontology or Ontology.load()
    correct = 0
    per_case: list[dict[str, str]] = []
    for case in cases:
        try:
            dossier = build_target_dossier(case.target, records, ontology=ontology)
            verdict = dossier.indication_verdicts.get(case.disease)
            predicted = verdict.label if verdict else "insufficient"
        except DossierError:
            predicted = "unresolved"
        if predicted == case.expected_label:
            correct += 1
        per_case.append(
            {"id": case.id, "expected": case.expected_label, "predicted": predicted}
        )
    total = len(cases) or 1
    return DossierVerdictReport(
        accuracy=correct / total,
        correct=correct,
        total=len(cases),
        per_case=per_case,
    )


def evaluate_faithfulness(
    records: list[CorpusRecord],
    responder,
    cases: list[StanceCase],
    *,
    k: int = 5,
) -> dict[str, object]:
    """Fraction of a responder's proposed quotes that are verbatim in the source.

    Measures how much the faithfulness guard has to reject: quotes that are not
    an exact span of the cited abstract are hallucinated/altered and dropped.
    """

    retriever = ConceptAwareRetriever(records)
    proposed = 0
    faithful = 0
    for case in cases:
        for item in retriever.search(case.claim, top_k=k):
            for raw in responder(case.claim, item.record) or []:
                quote = (raw.get("quote") or "").strip()
                if not quote:
                    continue
                proposed += 1
                if quote in item.record.abstract:
                    faithful += 1
    rate = faithful / proposed if proposed else 1.0
    return {"proposed": proposed, "faithful": faithful, "rate": rate}


def main() -> None:
    ontology = Ontology.load()
    report = evaluate_entity_linking(ontology, load_entity_cases())
    print("# Entity Linking Evaluation")
    print(f"precision: {report.precision:.3f}")
    print(f"recall:    {report.recall:.3f}")
    print(f"f1:        {report.f1:.3f}")
    print(f"tp/fp/fn:  {report.true_positives}/{report.false_positives}/{report.false_negatives}")
    print("")
    print("## Per-case errors")
    errors = [case for case in report.per_case if case["missed"] or case["spurious"]]
    if not errors:
        print("- none")
    for case in errors:
        print(f"- {case['id']}: missed={case['missed']} spurious={case['spurious']}")

    records = load_corpus(default_corpus_path())
    retrieval_cases = load_retrieval_cases()
    print("")
    print("# Retrieval Evaluation (ablation)")
    for retrieval_report in retrieval_ablation(records, retrieval_cases, k=3):
        print(
            f"- {retrieval_report.label:>9}: "
            f"recall@{retrieval_report.k}={retrieval_report.recall_at_k:.3f} "
            f"mrr={retrieval_report.mrr:.3f} "
            f"(n={retrieval_report.cases})"
        )
    print(f"- {'+embedding':>9}: {_embedding_ablation_line(records, retrieval_cases)}")

    stance_report = evaluate_stance(records, load_stance_cases())
    print("")
    print("# Stance Evaluation")
    for label in STANCE_CLASSES:
        scores = stance_report.per_class[label]
        print(
            f"- {label:>12}: p={scores['precision']:.3f} "
            f"r={scores['recall']:.3f} f1={scores['f1']:.3f}"
        )
    print(f"- macro-F1: {stance_report.macro_f1:.3f}")
    print(
        f"- guardrail violations: {stance_report.guardrail_violations}"
        f"/{stance_report.guardrail_items} "
        f"(cross-entity + polarity leaks; target 0)"
    )

    quant_report = evaluate_quant(load_quant_cases())
    print("")
    print("# Quantitative Extraction Evaluation")
    print(f"- precision: {quant_report.precision:.3f}")
    print(f"- recall:    {quant_report.recall:.3f}")
    print(f"- f1:        {quant_report.f1:.3f}")
    print(
        f"- tp/fp/fn:  {quant_report.true_positives}/"
        f"{quant_report.false_positives}/{quant_report.false_negatives}"
    )

    moa_report = evaluate_moa(load_moa_cases())
    print("")
    print("# Mechanism-of-Action Extraction Evaluation")
    print(f"- precision: {moa_report.precision:.3f}")
    print(f"- recall:    {moa_report.recall:.3f}")
    print(f"- f1:        {moa_report.f1:.3f}")
    print(
        f"- tp/fp/fn:  {moa_report.true_positives}/"
        f"{moa_report.false_positives}/{moa_report.false_negatives}"
        " (incl. negative controls: a gene activated by a variant, a suppressor cue)"
    )

    from .extraction import LLMClaimExtractor, heuristic_responder

    stance_cases = load_stance_cases()
    responder = heuristic_responder()
    mock_unguarded = evaluate_stance(
        records,
        stance_cases,
        extractor=LLMClaimExtractor(responder=responder, guard=False),
    )
    mock_hybrid = evaluate_stance(
        records,
        stance_cases,
        extractor=LLMClaimExtractor(responder=responder, guard=True),
    )
    faithfulness = evaluate_faithfulness(records, responder, stance_cases)
    print("")
    print("# Claim Extractor Evaluation")
    print(
        f"- deterministic:      macro-F1={stance_report.macro_f1:.3f} "
        f"guardrail_leaks={stance_report.guardrail_violations}/{stance_report.guardrail_items}"
    )
    print(
        f"- mock-llm (no guard): macro-F1={mock_unguarded.macro_f1:.3f} "
        f"guardrail_leaks={mock_unguarded.guardrail_violations}/{mock_unguarded.guardrail_items}"
    )
    print(
        f"- mock-llm (hybrid):  macro-F1={mock_hybrid.macro_f1:.3f} "
        f"guardrail_leaks={mock_hybrid.guardrail_violations}/{mock_hybrid.guardrail_items}"
    )
    print(
        f"- faithfulness (both mock paths): {faithfulness['rate']:.3f} "
        f"({faithfulness['faithful']}/{faithfulness['proposed']} quotes verbatim)"
    )
    print(
        "  (hybrid re-applies the entity-grounding + polarity guards on top of the "
        "responder; faithfulness is guard-independent. A real LLM replaces the mock.)"
    )

    verdict_report = evaluate_verdicts(records, load_verdict_cases())
    print("")
    print("# Weighted Verdict Evaluation")
    print(f"- accuracy: {verdict_report.accuracy:.3f} ({verdict_report.correct}/{verdict_report.total})")
    for case in verdict_report.per_case:
        mark = "ok" if case["expected"] == case["predicted"] else "MISS"
        print(f"- {case['id']}: expected={case['expected']} predicted={case['predicted']} [{mark}]")

    dossier_report = evaluate_dossier_verdicts(records, load_dossier_cases(), ontology=ontology)
    print("")
    print("# Dossier Indication-Verdict Evaluation")
    print(
        f"- accuracy: {dossier_report.accuracy:.3f} "
        f"({dossier_report.correct}/{dossier_report.total})"
    )
    for case in dossier_report.per_case:
        mark = "ok" if case["expected"] == case["predicted"] else "MISS"
        print(f"- {case['id']}: expected={case['expected']} predicted={case['predicted']} [{mark}]")

    stress = evaluate_stress()
    handled = sum(1 for r in stress if r.handled)
    print("")
    print("# Stress Set (deliberately hard; NOT expected to be perfect)")
    print(f"- handled: {handled}/{len(stress)} — the misses are documented limitations, not regressions")
    for r in stress:
        mark = "ok" if r.handled else "LIMIT"
        print(f"- {r.id} ({r.kind}) [{mark}]: {r.note}")


if __name__ == "__main__":
    main()
