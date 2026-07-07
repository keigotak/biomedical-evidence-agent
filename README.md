# Biomedical Evidence Agent

A small research-oriented demo for biology-facing biomedical evidence synthesis.

This project explores how LLMs, retrieval, structured evidence extraction, and evaluation workflows can support scientific reasoning in biomedical research.

It uses toy/sample data only and does not include any proprietary or confidential work.

The main workflow is claim-centered evidence synthesis: given a biomedical claim, retrieve candidate evidence and organize extracted sentences into supporting, conflicting, and insufficient/indirect evidence. This is a research engineering demo, not medical advice, clinical decision support, or a reproduction of proprietary work.

## What It Demonstrates

- Ontology-based entity normalization: abbreviations, synonyms, and brand/generic forms (`AZD9291` / `osimertinib` / `Tagrisso`) resolve to one concept id with UniProt/ChEMBL/MeSH cross-references — the same-entity backbone for evidence integration
- Retrieval over PubMed-abstract-style sample records, in a lexical, a concept-aware (ontology-grounded), and an optional embedding flavor
- Claim-centered evidence grouping into supporting, conflicting, and insufficient/indirect evidence, with attribution guards (entity grounding + outcome polarity) that generalize beyond oncology
- A weighted **verdict** that aggregates supporting vs conflicting evidence by study-design tier over independent sources into a graded, auditable bottom line (`well-supported` / `mixed` / `contested` / `insufficient`)
- A target-centric **dossier** that pivots from a claim to a normalized target concept and rolls up its modulators (with potencies), disease contexts, evidence angles, and study tiers across the corpus
- Provenance spans (`source_id@start-end`) back to the source text for every extracted sentence
- Evidence-tier weighting by study design (`clinical` > `in_vivo` > `association` > `in_vitro` > `in_silico`) folded into confidence
- Multi-angle evidence facets (mechanism, clinical, biomarker, method) and an "Evidence by Angle" view
- Quantitative pharmacology extraction (IC50, EC50, Ki, Cmax, half-life, ...) with value, unit, and per-compound attribution for cross-compound comparison
- An optional model-backed (LLM) claim extractor with a citation-grounding guard that drops any quote not verbatim in its source — swappable for the deterministic default without weakening provenance
- Optional PubMed title/abstract retrieval using public metadata only
- An evaluation suite (entity linking, retrieval ablation, stance with guardrails, quantitative, extractor faithfulness)

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
│   ├── ontology.jsonl             # Curated concept registry (ids + xrefs)
│   ├── evaluation_claims.jsonl    # Retrieval evaluation set
│   ├── evaluation_entities.jsonl  # Entity-linking evaluation set
│   ├── evaluation_stances.jsonl   # Stance + guardrail evaluation set
│   ├── evaluation_quant.jsonl     # Quantitative-extraction evaluation set
│   ├── evaluation_verdicts.jsonl  # Weighted-verdict evaluation set
│   └── evaluation_dossiers.jsonl  # Dossier per-indication verdict set
├── docs/
│   ├── architecture.md            # Workflow and component design
│   └── example_output.md          # Example evidence cards
├── src/
│   └── biomedical_evidence_agent/
│       ├── cli.py                 # Command-line entry point
│       ├── ontology.py            # Concept normalization
│       ├── aliases.py             # Abbreviation/synonym alias tags (lexical baseline)
│       ├── retrieval.py           # Lexical + concept-aware retrievers
│       ├── embedding.py           # Optional embedding retriever ([semantic] extra)
│       ├── evidence.py            # Evidence card generation + weighted verdict
│       ├── extraction.py          # Optional model-backed claim extractor ([llm] extra)
│       ├── dossier.py             # Target-centric evidence roll-up
│       ├── quant.py               # Quantitative parameter extraction
│       ├── pubmed.py              # Optional PubMed metadata retrieval
│       ├── evaluation.py          # Entity-linking / retrieval / stance / quant evaluation
│       └── schemas.py             # Dataclasses for records and cards
└── tests/
    ├── test_pipeline.py
    └── test_ontology.py
```

## Design Notes

The default workflow uses deterministic extraction, stance labeling, and concept-aware lexical retrieval so the repository runs without API keys or network access. In a real LLM workflow, the deterministic `extract_claims` step can be replaced with a model-backed extractor while keeping the same structured evidence card interface.

Entity normalization is the same-entity backbone: concepts carry a local id plus external cross-references, so the curated registry can be swapped for a real terminology service without changing the id contract. The bundled xref ids are illustrative demo data, not an authoritative mapping.

See [docs/example_output.md](docs/example_output.md) for compact example evidence cards, and [docs/architecture.md](docs/architecture.md) for the component design.

## Local Usage

Python 3.10 or newer is recommended.

```bash
python -m pip install -e .
python -m biomedical_evidence_agent.cli --claim "BRAF melanoma is associated with response to targeted inhibitor treatment." --top-k 3

# Retriever flavor for the local corpus (default: concept)
python -m biomedical_evidence_agent.cli --claim "..." --retriever lexical

# Optional embedding retriever (needs the semantic extra)
python -m pip install -e '.[semantic]'
python -m biomedical_evidence_agent.cli --claim "..." --retriever embedding

# Model-backed claim extractor. 'mock-llm' runs the full grounding pipeline
# offline; 'llm' uses a real model (needs the llm extra + ANTHROPIC_API_KEY).
python -m biomedical_evidence_agent.cli --claim "..." --extractor mock-llm
python -m pip install -e '.[llm]'
python -m biomedical_evidence_agent.cli --claim "..." --extractor llm

# Target-centric dossier (local corpus): modulators, potencies, contexts, tiers
python -m biomedical_evidence_agent.cli --target EGFR

# Evaluation suite: entity linking, retrieval ablation, stance guardrails, quantitative, verdict, dossier indication verdict
python -m biomedical_evidence_agent.evaluation

python -m unittest discover -s tests
```

## Scope

This repository is a public demo for portfolio and research-engineering discussion. It does not include medical advice, patient data, proprietary datasets, or confidential work.

## License

MIT
