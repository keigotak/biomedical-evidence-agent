# Biomedical Evidence Agent

A small research-oriented demo for biology-facing biomedical evidence synthesis.

This project explores how LLMs, retrieval, structured evidence extraction, and evaluation workflows can support scientific reasoning in biomedical research.

It uses toy/sample data only and does not include any proprietary or confidential work.

## What It Demonstrates

- Retrieval over PubMed-abstract-style sample records
- Evidence card generation for gene, disease, and drug questions
- Claim extraction from retrieved abstracts
- Evidence type and confidence labeling
- A small evaluation set for retrieval and claim-support checks

The implementation is intentionally compact. It is meant to show the shape of a biology-facing biomedical AI workflow, not to provide clinical or production guidance.

## Example

```bash
python -m biomedical_evidence_agent.cli \
  --query "EGFR non-small cell lung cancer tyrosine kinase inhibitor resistance" \
  --top-k 3
```

This produces a structured evidence card with retrieved records, extracted claims, evidence labels, and limitations.

## Project Structure

```text
.
├── data/
│   ├── sample_corpus.jsonl        # Toy biomedical abstract records
│   └── evaluation_claims.jsonl    # Small retrieval/claim evaluation set
├── docs/
│   └── architecture.md            # Workflow and component design
├── src/
│   └── biomedical_evidence_agent/
│       ├── cli.py                 # Command-line entry point
│       ├── evidence.py            # Evidence card generation
│       ├── retrieval.py           # Lightweight lexical retriever
│       └── schemas.py             # Dataclasses for records and cards
└── tests/
    └── test_pipeline.py
```

## Design Notes

The current code uses deterministic extraction and lexical retrieval so the repository can run without API keys. In a real LLM workflow, the deterministic `extract_claims` step can be replaced with a model-backed extractor while keeping the same structured evidence card interface.

## Local Usage

Python 3.10 or newer is recommended.

```bash
python -m pip install -e .
python -m biomedical_evidence_agent.cli --query "BRAF melanoma targeted therapy" --top-k 2
python -m unittest discover -s tests
```

## Scope

This repository is a public demo for portfolio and research-engineering discussion. It does not include medical advice, patient data, proprietary datasets, or confidential work.

## License

MIT
