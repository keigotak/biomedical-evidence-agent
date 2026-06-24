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

### PubMed Tool

`pubmed.py` implements an optional public-metadata retrieval path using NCBI E-utilities. It fetches title, abstract, PMID, and year metadata only. The default workflow does not require network access.

### Claim Extractor

`evidence.py` extracts candidate claims from retrieved abstracts by selecting sentences that mention query or claim terms. It then assigns a lightweight stance label: `supports`, `conflicts`, or `insufficient`. This is intentionally deterministic. The interface is designed so a model-backed extractor can replace it later.

### Evidence Card

The evidence card is the primary output object. It contains the query or claim, retrieved records, extracted evidence sentences grouped by stance, confidence labels, limitations, and suggested next checks.

### Evaluation

The sample evaluation data checks whether expected record identifiers appear in the retrieved set for a query. This is a minimal scaffold for retrieval and evidence-support evaluation.

## Data Policy

All bundled data in this repository is toy/sample text. Optional PubMed mode uses public metadata only. The project is not copied from proprietary work, is not clinical decision support, and should not be treated as biomedical ground truth.
