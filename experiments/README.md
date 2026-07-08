# Experiments

Side modules that hang off the BioClaim Auditor core. They are **not part of the
audited MVP** — the CLI, the Claim Audit Report, and the test suite do not depend
on anything here. Everything in this folder imports the library
(`biomedical_evidence_agent`) and layers a more exploratory view on top, so a
broken experiment can never break the main demo.

Run them directly with the package on the path:

```bash
PYTHONPATH=src python experiments/hypothesis_stress_test.py \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
```

## What's here

- **`hypothesis_stress_test.py`** — stress-tests a claim from several research
  angles (mechanism, human evidence, animal model, clinical trial, safety,
  translatability). Each angle re-runs retrieval + the rule-based audit with an
  angle-focused query, so you can see where a claim is strong and where it is
  only asserted. Offline; no API key required.

## Ideas parked here (not yet built)

- **Reviewer duel** — two Claude reviewers argue the claim (advocate vs skeptic),
  and a judge scores which evidence survives.
- **Evidence map UI** — a visual map of which sentence supports which part of the
  claim (belongs in the Streamlit app, not here).
