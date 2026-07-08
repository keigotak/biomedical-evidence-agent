# Claim Audit Report

## Claim
> BRAF V600E melanoma is associated with response to targeted inhibitor treatment.

## Audit Verdict
**contested** (strength +0.00) — supports: 1×clinical; conflicts: 1×clinical; 2 indirect

## Evidence Map
- Independent sources: 1 supporting, 1 conflicting
- Sentences: 1 supporting · 1 conflicting · 2 indirect
- Records retrieved: 3
- Coverage by claim entity:
  - BRAF (gene): 1 supporting, 1 conflicting [toy-002, toy-006]
  - melanoma (disease): 1 supporting, 1 conflicting [toy-002, toy-006]
  - targeted therapy (drug_class): 1 supporting, 1 conflicting [toy-002, toy-006]

## Supporting Evidence
- [high | clinical | toy-002@0-116] This sample record describes BRAF V600E melanoma as a setting where targeted inhibitors can produce tumor responses.

## Conflicting Evidence
- [high | clinical | toy-006@0-150] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.

## Indirect / Insufficient Evidence
- [medium | clinical | toy-001@0-136] In this toy abstract, EGFR activating variants are associated with response to tyrosine kinase inhibitors in non-small cell lung cancer.
- [medium | clinical | toy-001@137-285] Acquired resistance is described after first-line inhibitor exposure, and follow-up testing is needed to identify resistance-associated alterations.

## Citation Audit
- 2/2 cited quotes are verbatim spans of their source (100% faithful).

## Overclaim Flags
- None.

## Contradiction Flags
- 🟡 Evidence conflicts: 1 supporting vs 1 conflicting independent source(s).

## Retrieval Gaps
- None.

## Reviewer Critique (mock)
_Verdict 'contested' with 1 audit flag(s); treat the claim as provisional pending the checks below._
- **missing-counter-evidence:** Sources disagree; do not treat this as settled. Search specifically for the weaker side before concluding.
- **weak-citation:** All 2 citations are verbatim, but they are single sentences — check they are not quoted out of context.
- **next-source:** Pull an independent, higher-tier source that names the exact claim entities; start beyond toy-006.

## What Would Change My Mind?
- An independent, well-powered study that breaks the tie, plus a mechanism explaining why the existing reports disagree.

## Suggested Next Checks
- Review cited records manually before drawing scientific conclusions.
- Add model-based claim extraction with citation-grounded outputs.
- Evaluate evidence support with a curated benchmark.

## Limitations
- Uses toy/sample abstracts by default; optional PubMed mode uses public metadata.
- Deterministic stance labeling is a scaffold for a future model-backed extractor.
- Evidence labels are illustrative research signals, not clinical guidance.
- Research signal only — not medical advice, not a validated clinical assessment.
