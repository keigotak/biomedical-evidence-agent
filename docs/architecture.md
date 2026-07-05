# Architecture

Biomedical Evidence Agent is a small evidence synthesis workflow for biology-facing biomedical AI demonstrations.

## Workflow

```text
User query or biomedical claim
  -> concept normalization (ontology grounding of entities)
  -> retrieval over sample abstracts (lexical / concept-aware / optional embedding) or PubMed metadata
  -> claim extraction from retrieved evidence
  -> supporting / conflicting / insufficient grouping with attribution guards
  -> evidence-tier, facet, and confidence labeling with provenance spans
  -> quantitative parameter extraction (IC50/EC50/Ki/Cmax/half-life/...)
  -> structured evidence card
  -> evaluation (entity linking / retrieval / stance / quantitative)
```

## Components

### Ontology (concept normalization)

`ontology.py` loads a curated concept registry (`data/ontology.jsonl`) and resolves surface text to concepts with longest-match, type-aware normalization. Each concept has a local id (`BEA:<type>:<slug>`) plus external cross-references (UniProt, ChEMBL, MeSH, HGNC). The local id is the stable resolution unit; the xrefs make the registry swappable for a real terminology service later.

This is the same-entity backbone the rest of the pipeline stands on: abbreviations, synonyms, and brand/generic forms (`AZD9291` / `osimertinib` / `Tagrisso`) collapse onto one concept id, so retrieval, grounding, and quantitative attribution all reason about the same entity. The bundled xref ids are illustrative demo data, not an authoritative mapping.

### Retriever

`retrieval.py` implements a TF-IDF cosine retriever using only the Python standard library, in two flavors: `LexicalRetriever` (tokens plus abbreviation alias tags) and `ConceptAwareRetriever` (tokens plus normalized concept ids). The concept ids give the cosine a representation-invariant signal, so a record that names the query's entities with different surface forms is still retrieved — ontology-grounded semantic matching without a model.

`embedding.py` adds an optional dense retriever behind the `semantic` extra. It imports `sentence-transformers` lazily and raises `EmbeddingUnavailable` with install guidance when the extra is absent, so the default workflow stays dependency-free and offline.

### PubMed Tool

`pubmed.py` implements an optional public-metadata retrieval path using NCBI E-utilities. It fetches title, abstract, PMID, and year metadata only. The default workflow does not require network access.

### Claim Extractor

`evidence.py` extracts candidate claims from retrieved abstracts and assigns a lightweight stance label (`supports`, `conflicts`, `insufficient`). Two attribution guards apply before a sentence can count as supporting or conflicting evidence:

- **Entity grounding:** the sentence must name the claim's principal entity, checked by normalized concept identity (with a gene-token fallback for variants the ontology does not carry). Because grounding is concept-based rather than a hardcoded disease word list, it generalizes across domains instead of only oncology.
- **Outcome polarity:** a sentence describing the opposite therapeutic direction (`response` vs `resistance`) is demoted to insufficient rather than counted as support.

Each sentence is tagged with evidence **facets** (`mechanism`, `clinical`, `biomarker`, `method`), an evidence **tier** (`clinical` > `in_vivo` > `association` > `in_vitro` > `in_silico`, from study design or text cues), and a **provenance span** (character offsets back to the source record). Confidence combines retrieval relevance, stance decisiveness, anchor count, facet coverage, and tier weight.

### Quantitative Extractor

`quant.py` lifts quantitative pharmacology parameters out of prose into structured records: potency (IC50, EC50, Ki, Kd) and PK/exposure (Cmax, AUC, half-life, clearance, bioavailability), each with relation, value, unit, and a provenance span. Each measurement is attributed to the nearest preceding compound so values are comparable across compounds and assays.

### Evidence Card

The evidence card is the primary output object. It contains the query or claim, retrieved records, stance-grouped sentences with facet/tier/confidence/provenance, an "Evidence by Angle" facet view, a "Quantitative Evidence" comparison, limitations, and next checks.

### Evaluation

`evaluation.py` scores the pipeline on four separated targets, so a change to one stage does not hide a regression in another:

- **Entity linking:** set-level precision/recall/F1 of concept resolution, with negative controls (`data/evaluation_entities.jsonl`).
- **Retrieval:** Recall@k and MRR with a lexical / +concept / +embedding ablation (`data/evaluation_claims.jsonl`).
- **Stance:** per-class precision/recall/F1 plus guardrail metrics — cross-entity and opposite-polarity leaks, target zero (`data/evaluation_stances.jsonl`).
- **Quantitative:** precision/recall/F1 on extracted (parameter, value, unit) tuples, with a negative control (`data/evaluation_quant.jsonl`).

Run it with `python -m biomedical_evidence_agent.evaluation`.

## Data Policy

All bundled data in this repository is toy/sample text, and the ontology xref ids are illustrative. Optional PubMed mode uses public metadata only. The project is not copied from proprietary work, is not clinical decision support, and should not be treated as biomedical ground truth.
