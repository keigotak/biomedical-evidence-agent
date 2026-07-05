# Biomedical Evidence Agent

A small research-oriented demo for biology-facing biomedical evidence synthesis.

This project explores how LLMs, retrieval, structured evidence extraction, and evaluation workflows can support scientific reasoning in biomedical research.

It uses toy/sample data only and does not include any proprietary or confidential work.

The main workflow is claim-centered evidence synthesis: given a biomedical claim, retrieve candidate evidence and organize extracted sentences into supporting, conflicting, and insufficient/indirect evidence. This is a research engineering demo, not medical advice, clinical decision support, or a reproduction of proprietary work.

## What It Demonstrates

- Retrieval over PubMed-abstract-style sample records, with abbreviation/synonym expansion (e.g. `NSCLC` ↔ `non-small cell lung cancer`, `TKI` ↔ `tyrosine kinase inhibitor`)
- Evidence card generation for gene, disease, and drug questions
- Claim extraction from retrieved abstracts
- Claim-centered evidence grouping into supporting, conflicting, and insufficient/indirect evidence
- Multi-angle evidence facets (mechanism, clinical, biomarker, method) and an "Evidence by Angle" view
- Evidence type and confidence labeling
- Optional PubMed title/abstract retrieval using public metadata only
- A small evaluation set for retrieval and claim-support checks

The implementation is intentionally compact. It is meant to show the shape of a biology-facing biomedical AI workflow, not to provide clinical or production guidance.

## Example

```bash
python -m biomedical_evidence_agent.cli \
  --claim "EGFR T790M is associated with resistance to first-generation EGFR inhibitors in non-small cell lung cancer." \
  --top-k 3
```

This produces a structured evidence card with retrieved records, extracted claims, evidence stance labels, and limitations.

Optional PubMed metadata mode:

```bash
python -m biomedical_evidence_agent.cli \
  --source pubmed \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 5
```

PubMed mode uses public title/abstract metadata only. The default mode remains the local toy/sample corpus.

## Project Structure

```text
.
├── data/
│   ├── sample_corpus.jsonl        # Toy biomedical abstract records
│   └── evaluation_claims.jsonl    # Small retrieval/claim evaluation set
├── docs/
│   ├── architecture.md            # Workflow and component design
│   └── example_output.md          # Example evidence card
├── src/
│   └── biomedical_evidence_agent/
│       ├── cli.py                 # Command-line entry point
│       ├── evidence.py            # Evidence card generation
│       ├── pubmed.py              # Optional PubMed metadata retrieval
│       ├── retrieval.py           # Lightweight lexical retriever
│       └── schemas.py             # Dataclasses for records and cards
└── tests/
    └── test_pipeline.py
```

## Design Notes

The current code uses deterministic extraction, stance labeling, and lexical retrieval so the repository can run without API keys. In a real LLM workflow, the deterministic `extract_claims` step can be replaced with a model-backed extractor while keeping the same structured evidence card interface.

See [docs/example_output.md](docs/example_output.md) for a compact example evidence card.

## Local Usage

Python 3.10 or newer is recommended.

```bash
python -m pip install -e .
python -m biomedical_evidence_agent.cli --claim "BRAF melanoma is associated with response to targeted inhibitor treatment." --top-k 3
python -m unittest discover -s tests
```

## Scope

This repository is a public demo for portfolio and research-engineering discussion. It does not include medical advice, patient data, proprietary datasets, or confidential work.

## License

MIT
