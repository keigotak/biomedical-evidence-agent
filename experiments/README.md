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
  fabricated citation. Offline mock agents by default (`--mode mock`); pass
  `--mode claude` to run all three agents on the real API (needs the `llm` extra
  + `ANTHROPIC_API_KEY`). A saved real-Claude transcript is in
  [`../outputs/example_reviewer_duel_claude.md`](../outputs/example_reviewer_duel_claude.md)
  — there the judge distinguishes "association with response" from "durable
  response" and rules for the advocate, a call the deterministic mock doesn't make.

  ```bash
  PYTHONPATH=src python experiments/reviewer_duel.py --mode claude \
    --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
  ```

- **`compare_claims.py`** — audits several claims at once and prints one
  comparison table (verdict, supporting/conflicting sources, top audit flag,
  citation faithfulness), so you can scan a batch and see which claims hold up,
  which are contested, and which overreach. Offline; no API key required.

  ```bash
  PYTHONPATH=src python experiments/compare_claims.py   # default demo set
  ```

- **`document_audit.py`** — paste a *paragraph* (a paper's discussion, a review's
  conclusion, a press release) and it pulls out the sentences that actually make
  a biological claim — each must ground a gene/drug concept **and** carry an
  assertion cue — audits every one, and prints a batch report that surfaces the
  overclaims and contradictions hiding in an otherwise smooth paragraph. Claim
  segmentation reuses the ontology backbone, so it stays offline and can't invent
  a claim the text didn't make (the honest tradeoff: it skips claims phrased
  without a cue word). Snapshot:
  [`../outputs/example_document_audit.md`](../outputs/example_document_audit.md).

  ```bash
  PYTHONPATH=src python experiments/document_audit.py                 # default passage
  PYTHONPATH=src python experiments/document_audit.py --file notes.txt
  ```

## Ideas parked here (not yet built)

- (The Evidence Map visualization graduated into the Streamlit app —
  `report.evidence_map_html`.)
