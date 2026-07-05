# Example Output

These examples use the local toy/sample corpus. They show the shape of the evidence card, not a biomedical claim. Each extracted sentence carries a `source_id@start-end` provenance span, an evidence tier (study-design strength), and a confidence grade.

## Example 1: Stance separation

```bash
python -m biomedical_evidence_agent.cli \
  --claim "BRAF melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 3
```

```text
# Evidence Card

Source: sample
Query: BRAF melanoma is associated with response to targeted inhibitor treatment.
Claim: BRAF melanoma is associated with response to targeted inhibitor treatment.

## Verdict
- contested (strength +0.00) — supports: 1×clinical; conflicts: 1×clinical; 2 indirect
- Weighted by study-design tier over independent sources; not clinical guidance.

## Retrieved Evidence
- toy-006 (2024) score=0.5561: Conflicting toy evidence for a biomarker claim
- toy-002 (2020) score=0.413: BRAF V600E as a biomarker in melanoma treatment
- toy-001 (2021) score=0.278: EGFR alterations and targeted therapy response in lung cancer

## Supporting Evidence
- [high | clinical | biomarker | clinical | toy-002@0-116] This sample record describes BRAF V600E melanoma as a setting where targeted inhibitors can produce tumor responses.

## Conflicting Evidence
- [high | clinical | conflicting_evidence | clinical, biomarker | toy-006@0-150] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.

## Insufficient or Indirect Evidence
- [medium | clinical | therapeutic | mechanism, clinical, biomarker | toy-001@0-136] In this toy abstract, EGFR activating variants are associated with response to tyrosine kinase inhibitors in non-small cell lung cancer.
- [medium | clinical | therapeutic | clinical | toy-001@137-285] Acquired resistance is described after first-line inhibitor exposure, and follow-up testing is needed to identify resistance-associated alterations.

## Evidence by Angle
- clinical:
  - [conflicts | toy-006] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.
  - [supports | toy-002] This sample record describes BRAF V600E melanoma as a setting where targeted inhibitors can produce tumor responses.
- biomarker:
  - [conflicts | toy-006] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.

## Quantitative Evidence
- No quantitative parameters extracted.

## Limitations
- Uses toy/sample abstracts by default; optional PubMed mode uses public metadata.
- Deterministic stance labeling is a scaffold for a future model-backed extractor.
- Evidence labels are illustrative research signals, not clinical guidance.

## Next Checks
- Review cited records manually before drawing scientific conclusions.
- Add model-based claim extraction with citation-grounded outputs.
- Evaluate evidence support with a curated benchmark.
```

The EGFR sentence (`toy-001`) names a different gene than the `BRAF` claim, so entity grounding demotes it to insufficient instead of counting it as support.

## Example 2: Quantitative pharmacology

```bash
python -m biomedical_evidence_agent.cli \
  --claim "Osimertinib is a more potent EGFR inhibitor than gefitinib in NSCLC." \
  --top-k 2
```

```text
## Quantitative Evidence
- IC50:
  - osimertinib: 12 nM [toy-007@76-89]
  - gefitinib: 38 nM [toy-007@143-156]
- half-life:
  - osimertinib: 48 h [toy-007@181-213]
```

Values are lifted out of prose into structured records, attributed to the nearest compound, and sorted so potencies are directly comparable. The source sentences are tagged with the `in_vitro` tier, which lowers their confidence relative to clinical evidence.

## What To Notice

- The card leads with a weighted verdict: here `contested`, because one clinical support is offset by one clinical conflict — a single in-vitro result could not have produced that balance.
- The output is organized around a claim, not a generic keyword search.
- Supporting and conflicting evidence are separated from indirect context, with cross-entity and opposite-polarity sentences demoted by attribution guards.
- Each sentence carries a provenance span, an evidence tier, and a confidence grade.
- Quantitative parameters are extracted and compared across compounds.
- The card preserves limitations and next checks instead of presenting a final biomedical conclusion.
