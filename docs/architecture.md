# Architecture

Biomedical Evidence Agent is a small evidence synthesis workflow for biology-facing biomedical AI demonstrations.

## Workflow

```text
User query
  -> lexical retrieval over sample abstracts
  -> claim extraction from retrieved evidence
  -> evidence type and confidence labeling
  -> structured evidence card
  -> lightweight evaluation
```

## Components

### Retriever

`retrieval.py` implements a small TF-IDF-style lexical retriever using only the Python standard library. It ranks sample abstracts by overlap with the query and returns scored records.

### Claim Extractor

`evidence.py` extracts candidate claims from retrieved abstracts by selecting sentences that mention query terms. This is intentionally deterministic. The interface is designed so a model-backed extractor can replace it later.

### Evidence Card

The evidence card is the primary output object. It contains the query, retrieved records, extracted claims, confidence labels, limitations, and suggested next checks.

### Evaluation

The sample evaluation data checks whether expected record identifiers appear in the retrieved set for a query. This is a minimal scaffold for retrieval and evidence-support evaluation.

## Data Policy

All data in this repository is toy/sample text. It is not copied from proprietary work and should not be treated as biomedical ground truth.
