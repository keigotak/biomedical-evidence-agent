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
- toy-006 (2024) score=0.5539: Conflicting toy evidence for a biomarker claim
- toy-002 (2020) score=0.4162: BRAF V600E as a biomarker in melanoma treatment
- toy-001 (2021) score=0.3154: EGFR alterations and targeted therapy response in lung cancer
- toy-004 (2019) score=0.0219: TP53 mutation status and tumor biology

## Supporting Evidence
- [high | biomarker | clinical | toy-002@0-116] This sample record describes BRAF V600E melanoma as a setting where targeted inhibitors can produce tumor responses.

## Conflicting Evidence
- [high | conflicting_evidence | clinical, biomarker | toy-006@0-150] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.

## Insufficient or Indirect Evidence
- [medium | therapeutic | mechanism, clinical, biomarker | toy-001@0-136] In this toy abstract, EGFR activating variants are associated with response to tyrosine kinase inhibitors in non-small cell lung cancer.
- [medium | therapeutic | clinical | toy-001@137-285] Acquired resistance is described after first-line inhibitor exposure, and follow-up testing is needed to identify resistance-associated alterations.

## Evidence by Angle
- clinical:
  - [conflicts | toy-006] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.
  - [supports | toy-002] This sample record describes BRAF V600E melanoma as a setting where targeted inhibitors can produce tumor responses.
- biomarker:
  - [conflicts | toy-006] This synthetic record describes a small cohort where BRAF status was not associated with durable response to targeted inhibitor treatment in melanoma.

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
- Each evidence line carries facet tags and a `source@start-end` character span back into the source abstract, so any label can be verified against the original text.
- The "Evidence by Angle" view regroups the same on-claim evidence by facet (mechanism, clinical, biomarker, method) to show whether support is one-dimensional or converges across angles.
- Confidence reflects evidence strength (stance, entity grounding, facet coverage), not retrieval rank alone.
- The card preserves limitations and next checks instead of presenting a final biomedical conclusion.
- Optional PubMed mode follows the same output shape while using public title/abstract metadata only.
