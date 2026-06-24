# Example Output

This example uses the local toy/sample corpus. It is intended to show the shape of the evidence card, not to make a biomedical claim.

## Command

```bash
python -m biomedical_evidence_agent.cli \
  --claim "BRAF melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 4
```

## Evidence Card

```text
# Evidence Card

Source: sample
Query: BRAF melanoma is associated with response to targeted inhibitor treatment.
Claim: BRAF melanoma is associated with response to targeted inhibitor treatment.

## Retrieved Evidence
- toy-006 (2024) score=0.5163: Conflicting toy evidence for a biomarker claim
- toy-002 (2020) score=0.367: BRAF V600E as a biomarker in melanoma treatment
- toy-001 (2021) score=0.2753: EGFR alterations and targeted therapy response in lung cancer
- toy-004 (2019) score=0.0244: TP53 mutation status and tumor biology

## Supporting Evidence
- [medium | biomarker | toy-002] This sample record describes BRAF V600E melanoma as a setting where targeted inhibitors can produce tumor responses.

## Conflicting Evidence
- [high | conflicting_evidence | toy-006] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.

## Insufficient or Indirect Evidence
- [medium | therapeutic | toy-001] In this toy abstract, EGFR activating variants are associated with response to tyrosine kinase inhibitors in non-small cell lung cancer.
- [medium | therapeutic | toy-001] Acquired resistance is described after first-line inhibitor exposure, and follow-up testing is needed to identify resistance-associated alterations.

## Limitations
- Uses toy/sample abstracts by default; optional PubMed mode uses public metadata.
- Deterministic stance labeling is a scaffold for a future model-backed extractor.
- Evidence labels are illustrative research signals, not clinical guidance.

## Next Checks
- Review cited records manually before drawing scientific conclusions.
- Add model-based claim extraction with citation-grounded outputs.
- Evaluate evidence support with a curated benchmark.
```

## What To Notice

- The output is organized around a claim, not a generic keyword search.
- Supporting and conflicting evidence are separated from indirect context.
- The card preserves limitations and next checks instead of presenting a final biomedical conclusion.
- Optional PubMed mode follows the same output shape while using public title/abstract metadata only.
