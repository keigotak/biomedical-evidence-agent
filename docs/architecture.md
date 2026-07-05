# Architecture

Biomedical Evidence Agent is a small evidence synthesis workflow for biology-facing biomedical AI demonstrations.

## Workflow

```text
User query or biomedical claim
  -> lexical retrieval over sample abstracts or optional PubMed metadata retrieval
  -> claim extraction from retrieved evidence
  -> supporting / conflicting / insufficient evidence grouping
  -> evidence type and confidence labeling
  -> structured evidence card
  -> lightweight evaluation
```

## Components

### Retriever

`retrieval.py` implements a small TF-IDF-style lexical retriever using only the Python standard library. It ranks sample abstracts by overlap with the query and returns scored records.

Both queries and documents are expanded with a small alias map (`aliases.py`) that bridges abbreviations, full names, and drug/class synonyms to a shared canonical tag (e.g. `NSCLC` ↔ `non-small cell lung cancer`, `TKI` ↔ `tyrosine kinase inhibitor`, `osimertinib` ↔ `EGFR`). This lets a claim written with abbreviations retrieve and ground against records that spell the terms out in full.

### PubMed Tool

`pubmed.py` implements an optional public-metadata retrieval path using NCBI E-utilities. It fetches title, abstract, PMID, and year metadata only. The default workflow does not require network access.

### Claim Extractor

`evidence.py` extracts candidate claims from retrieved abstracts by selecting sentences that mention query or claim terms. It then assigns a lightweight stance label: `supports`, `conflicts`, or `insufficient`. This is intentionally deterministic. The interface is designed so a model-backed extractor can replace it later.

Stance labeling applies two attribution guards before a sentence can count as supporting or conflicting evidence:

- **Entity grounding:** the sentence must mention the claim's principal entity (gene/variant token, or disease term when the claim names no gene). This prevents cross-entity mis-attribution, e.g. a `BRAF` sentence being attributed to an `EGFR` claim.
- **Outcome polarity:** the claim's therapeutic direction (`response` vs `resistance`) is compared with the sentence's. A sentence describing the opposite outcome is demoted to insufficient/indirect rather than counted as support, so a `response` sentence does not support a `resistance` claim.

Each extracted sentence is also tagged with one or more evidence **facets** — `mechanism`, `clinical`, `biomarker`, `method` — so the same claim can be examined from multiple angles independently of its stance.

### Evidence Card

The evidence card is the primary output object. It contains the query or claim, retrieved records, extracted evidence sentences grouped by stance, per-sentence facet tags, confidence labels, limitations, and suggested next checks. The card also renders an "Evidence by Angle" view that regroups the on-claim (supporting and conflicting) evidence by facet, so a reader can see whether support is one-dimensional or converges across mechanism, clinical, and biomarker lines.

Each evidence sentence carries a `source@start-end` character span back into its source abstract, so every stance label has verifiable provenance. Confidence is graded from evidence strength — retrieval relevance, whether the sentence takes a decisive stance, how many entity anchors it grounds against, and how many facets it covers — rather than from retrieval rank alone.

### Evaluation

`evaluation.py` runs the labeled set in `data/evaluation_claims.jsonl` end-to-end and reports three metrics per item plus aggregates:

- **retrieval hit@k** — fraction of `expected_ids` present in the retrieved set.
- **term coverage** — fraction of `expected_terms` whose tokens appear in the retrieved abstracts.
- **stance recall** — for claim-mode items, whether `expected_supporting_ids` / `expected_conflicting_ids` receive the right stance, and whether `expected_no_support` claims correctly yield no supporting evidence.

Run it with `python -m biomedical_evidence_agent.evaluation`. This turns evidence attribution into a measured quantity rather than an unverified behavior, and is the harness against which future changes (model-backed extraction, confidence calibration) can be judged.

## Data Policy

All bundled data in this repository is toy/sample text. Optional PubMed mode uses public metadata only. The project is not copied from proprietary work, is not clinical decision support, and should not be treated as biomedical ground truth.
