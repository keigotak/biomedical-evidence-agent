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

- **`reviewer_duel.py`** — an advocate and a skeptic argue the claim, and a judge
  rules. The advocate marshals supporting evidence, the skeptic marshals
  conflicts / overclaims / gaps, and the judge weighs both against the
  tier-weighted verdict. Every quote either side cites is re-checked against its
  source and dropped if it is not verbatim, so neither debater can win on a
  fabricated citation. Offline mock agents by default; the same shapes accept a
  Claude-backed responder.

## Ideas parked here (not yet built)

- **Evidence map UI** — a visual map of which sentence supports which part of the
  claim (belongs in the Streamlit app, not here).
- **Claude-backed duel** — wire `reviewer_duel` agents to real Anthropic
  responders (advocate/skeptic/judge system prompts) behind the `llm` extra.
