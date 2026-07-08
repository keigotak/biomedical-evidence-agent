# BioClaim Auditor

> Product demo built on the `biomedical-evidence-agent` repo.

**BioClaim Auditor is a Claude-powered claim-auditing tool for life sciences researchers.**

It is **not** a literature search engine. You give it a specific biological or translational claim, and instead of returning a smooth answer, it audits the claim: it exposes the supporting and conflicting evidence, checks that every citation is verbatim in its source, flags overclaims and contradictions, surfaces retrieval gaps, and tells you what would change the verdict.

![A BioClaim Auditor Claim Audit Report: the claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment" graded CONTESTED, an Evidence Map showing BRAF, melanoma and targeted-therapy each with one supporting and one conflicting source, an audit line reading citations 2/2 verbatim plus a contradiction flag, and a "what would change my mind" note.](docs/hero.svg)

<sub>Rendered from real audit output by [`scripts/render_hero.py`](scripts/render_hero.py) — the CLI/UI produce the same thing.</sub>

```bash
python -m biomedical_evidence_agent.cli \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 3 --report claim-audit --reviewer mock
```

A reviewable **Claim Audit Report** is the artifact ([`outputs/example_claim_audit.md`](outputs/example_claim_audit.md)) — Markdown or JSON (`--json`). The command above produces (abridged):

```text
# Claim Audit Report
## Audit Verdict
contested (strength +0.00) — supports: 1×clinical; conflicts: 1×clinical

## Supporting Evidence
- [high | clinical | toy-002@0-116] ...BRAF V600E melanoma as a setting where
  targeted inhibitors can produce tumor responses.
## Conflicting Evidence
- [high | clinical | toy-006@0-150] ...BRAF status was not associated with
  durable response to targeted inhibitor treatment in melanoma.

## Citation Audit
- 2/2 cited quotes are verbatim spans of their source (100% faithful).
## Contradiction Flags
- 🟡 Evidence conflicts: 1 supporting vs 1 conflicting independent source(s).

## Reviewer Critique (mock)
- missing-counter-evidence: Sources disagree; do not treat this as settled.
## What Would Change My Mind?
- An independent, well-powered study on BRAF, melanoma and targeted therapy that
  breaks the tie, plus a mechanism explaining why the existing reports disagree.
```

Note what a smooth answer would have hidden: the claim is **contested**, not confirmed; both cited quotes are verified verbatim; and the tool says exactly what evidence would move it.

## Core Workflow

**claim → retrieval → evidence extraction → stance labeling → citation / overclaim / contradiction audit → reviewer critique → Claim Audit Report**

Every step is grounded: entities are normalized to concept ids, every quote is a verbatim span of its source, and the reviewer's citations are re-checked so a critique cannot smuggle in a fabricated quote. The pitch: *instead of asking Claude to produce a smooth answer, BioClaim Auditor forces the model to expose evidence, uncertainty, contradictions, citation faithfulness, and next checks.*

The Claim Audit Report has these sections: **Claim · Audit Verdict · Evidence Map · Supporting / Conflicting / Indirect Evidence · Citation Audit · Overclaim Flags · Contradiction Flags · Retrieval Gaps · Reviewer Critique · What Would Change My Mind? · Suggested Next Checks · Limitations.**

Safety: research signal only — no medical advice, no patient data, toy/sample data by default.

## Under the Hood

This is a compact but real evidence-synthesis stack. The repo (`biomedical-evidence-agent`) uses toy/sample data only and includes no proprietary or confidential work.

- Ontology-based entity normalization: abbreviations, synonyms, and brand/generic forms (`AZD9291` / `osimertinib` / `Tagrisso`) resolve to one concept id with UniProt/ChEMBL/MeSH cross-references — the same-entity backbone for evidence integration
- Retrieval over PubMed-abstract-style sample records, in a lexical, a concept-aware (ontology-grounded), and an optional embedding flavor
- Claim-centered evidence grouping into supporting, conflicting, and insufficient/indirect evidence, with attribution guards (entity grounding + outcome polarity) that generalize beyond oncology
- A rule-based **claim audit** (`audit.py`): citation faithfulness, overclaim, contradiction, and retrieval-gap flags, each traceable to evidence
- A **reviewer agent** (`reviewer.py`) that critiques the card — offline `mock` or Claude-backed — with every cited quote re-grounded against its source
- A weighted **verdict** that aggregates supporting vs conflicting evidence by study-design tier over independent sources into a graded, auditable bottom line (`well-supported` / `mixed` / `contested` / `insufficient`)
- A target-centric **dossier** that pivots from a claim to a normalized target concept and rolls up its modulators (with potencies), disease contexts, evidence angles, and study tiers across the corpus
- Provenance spans (`source_id@start-end`) back to the source text for every extracted sentence
- Evidence-tier weighting by study design (`clinical` > `in_vivo` > `association` > `in_vitro` > `in_silico`) folded into confidence
- Multi-angle evidence facets (mechanism, clinical, biomarker, method) and an "Evidence by Angle" view
- Quantitative pharmacology extraction (IC50, EC50, Ki, Cmax, half-life, ...) with value, unit, and per-compound attribution for cross-compound comparison
- Grounded mechanism-of-action extraction (agonist / antagonist) attributing a drug to its ontology-declared target, feeding target-dossier modulator labels
- An optional model-backed (LLM) claim extractor with a citation-grounding guard that drops any quote not verbatim in its source — swappable for the deterministic default without weakening provenance
- Optional PubMed title/abstract retrieval using public metadata only
- An evaluation suite (entity linking, retrieval ablation, stance with guardrails, quantitative, MoA, weighted verdict, dossier indication verdict, extractor faithfulness)

The implementation is intentionally compact. It is meant to show the shape of a biology-facing biomedical AI workflow, not to provide clinical or production guidance.

See [`docs/differentiation.md`](docs/differentiation.md) for what makes this an *auditor* rather than a search tool, and [`docs/hackathon_demo.md`](docs/hackathon_demo.md) for a 2-minute demo script.

## Web UI (Docker)

The reviewable Claim Audit Report also runs as a Streamlit app. Docker keeps it self-contained — no local Streamlit install, and the dependency-free core stays intact:

```bash
docker compose up --build      # then open http://localhost:8501
```

Enter a claim, pick source / retriever / reviewer, and get the verdict, a visual **Evidence Map** (a per-entity bar showing which parts of the claim are supported, contested, or unaddressed — [standalone preview](outputs/example_evidence_map.html)), audit flags, the reviewer critique, and a downloadable Markdown/JSON report. To enable the Claude-backed reviewer, set `ANTHROPIC_API_KEY` in your environment before `docker compose up`.

Without Docker: `pip install '.[ui]' && streamlit run app.py`.

## Examples (CLI)

**Claim Audit Report** (the product surface):

```bash
python -m biomedical_evidence_agent.cli \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 3 --report claim-audit --reviewer mock
```

Try the contrast — a claim whose language outruns its evidence gets an overclaim flag:

```bash
python -m biomedical_evidence_agent.cli \
  --claim "TP53 mutation definitively cures colorectal cancer with salbutamol." \
  --top-k 3 --report claim-audit --reviewer mock
```

It generalizes across therapeutic areas — the same audit runs on oncology, immunology / fibrosis, and neurology claims. Both non-oncology examples come out `contested` (one supporting, one conflicting clinical source):

```bash
# immunology / fibrosis
python -m biomedical_evidence_agent.cli \
  --claim "IL-17A blockade may reduce fibrosis progression in systemic sclerosis." \
  --top-k 3 --report claim-audit --reviewer mock

# neurology
python -m biomedical_evidence_agent.cli \
  --claim "TREM2 is associated with Alzheimer's disease progression." \
  --top-k 3 --report claim-audit --reviewer mock
```

Add `--json` for the machine-readable report or `--reviewer claude` for a Claude-backed critique (needs the `llm` extra + `ANTHROPIC_API_KEY`). The Claude reviewer is real: on the BRAF claim it flags the supporting quote as hedged ("can produce tumor responses"), notes the conflict is about *durable* vs *initial* response, and points to the pivotal BRIM-3 trial as the next source — and every quote it cites is still re-verified verbatim against the source (its BRIM-3 suggestion carries no quote because it isn't in the corpus). See [`outputs/example_claim_audit_claude_reviewer.md`](outputs/example_claim_audit_claude_reviewer.md).

**Not just toy data — audit real literature.** `--source pubmed` runs the same audit against live PubMed (public title/abstract metadata):

```bash
python -m biomedical_evidence_agent.cli --source pubmed \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 5 --report claim-audit --reviewer mock
```

On real papers this returns `well-supported` with verbatim quotes from actual trials (e.g. FDA-approved BRAF/MEK combinations), each citation checked against its source abstract — see the snapshot in [`outputs/example_claim_audit_pubmed.md`](outputs/example_claim_audit_pubmed.md).

**Plain evidence card** (the default `--report evidence-card`) and **target dossier** (`--target EGFR`) are still available for the underlying stack.

**Experiments** (side modules, do not affect the main demo — see [`experiments/`](experiments/)):

```bash
# Stress-test a claim from several research angles
PYTHONPATH=src python experiments/hypothesis_stress_test.py \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."

# Advocate vs skeptic debate the claim; a judge rules (grounded citations only).
# Add --mode claude to run all three agents on the real API (llm extra + key).
PYTHONPATH=src python experiments/reviewer_duel.py \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."

# Audit several claims at once and compare them in one table
PYTHONPATH=src python experiments/compare_claims.py
```

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
│   ├── evaluation_dossiers.jsonl  # Dossier per-indication verdict set
│   └── evaluation_moa.jsonl       # Mechanism-of-action extraction set
├── docs/
│   ├── architecture.md            # Workflow and component design
│   ├── differentiation.md         # Why this is a claim auditor, not a search tool
│   ├── evaluation.md              # Eval design, n per stream, honest caveats + stress set
│   ├── hackathon_demo.md          # 2-minute demo script
│   ├── hero.svg                   # README hero (rendered from real output)
│   └── example_output.md          # Example evidence cards
├── scripts/
│   └── render_hero.py             # Regenerates docs/hero.svg from a real audit
├── outputs/
│   ├── example_claim_audit.md     # Saved Claim Audit Report (BRAF, demo artifact)
│   ├── example_claim_audit.json   # Same report as JSON
│   ├── example_claim_audit_il17a.md  # Non-oncology audit (IL-17A / fibrosis)
│   ├── example_claim_audit_pubmed.md # Live-PubMed audit snapshot (real papers)
│   ├── example_claim_audit_claude_reviewer.md # Real Claude reviewer critique
│   ├── example_reviewer_duel.md   # Advocate vs skeptic debate transcript (mock)
│   ├── example_reviewer_duel_claude.md # Same debate on real Claude (3 agents)
│   ├── example_evidence_map.html  # Visual per-entity Evidence Map (open in a browser)
│   └── example_claim_comparison.md # Several claims audited side by side
├── experiments/                   # Side modules; do not affect the main demo
│   ├── hypothesis_stress_test.py  # Multi-angle claim stress test
│   ├── compare_claims.py          # Audit several claims into one comparison table
│   └── reviewer_duel.py           # Advocate vs skeptic debate + judge
├── app.py                         # Streamlit UI (BioClaim Auditor)
├── Dockerfile                     # Containerized UI ([ui] extra only)
├── docker-compose.yml             # `docker compose up` -> http://localhost:8501
├── src/
│   └── biomedical_evidence_agent/
│       ├── cli.py                 # Command-line entry point
│       ├── ontology.py            # Concept normalization
│       ├── aliases.py             # Abbreviation/synonym alias tags (lexical baseline)
│       ├── retrieval.py           # Lexical + concept-aware retrievers
│       ├── embedding.py           # Optional embedding retriever ([semantic] extra)
│       ├── evidence.py            # Evidence card generation + weighted verdict
│       ├── audit.py               # Rule-based claim audit (citation/overclaim/contradiction/gaps)
│       ├── reviewer.py            # Reviewer agent (mock / Claude) with citation re-grounding
│       ├── report.py              # Claim Audit Report renderer (Markdown + JSON)
│       ├── extraction.py          # Optional model-backed claim extractor ([llm] extra)
│       ├── dossier.py             # Target-centric evidence roll-up
│       ├── quant.py               # Quantitative parameter extraction
│       ├── moa.py                 # Mechanism-of-action relation extraction
│       ├── pubmed.py              # Optional PubMed metadata retrieval
│       ├── evaluation.py          # Entity-linking / retrieval / stance / quant / MoA / verdict evaluation
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

# Evaluation suite (see docs/evaluation.md for design, n per stream, and honest
# caveats): entity linking, retrieval ablation, stance guardrails, quantitative,
# MoA, verdict, dossier verdict, extractor ablation, and a stress set of
# deliberately hard cases reported at its true 3/5 (not curated to perfect).
python -m biomedical_evidence_agent.evaluation

python -m unittest discover -s tests
```

## Scope

This repository is a public demo for portfolio and research-engineering discussion. It does not include medical advice, patient data, proprietary datasets, or confidential work.

## License

MIT
