# Architecture

Biomedical Evidence Agent is a small evidence synthesis workflow for biology-facing biomedical AI demonstrations.

## Workflow

```text
User query or biomedical claim
  -> concept normalization (ontology grounding of entities)
  -> retrieval over sample abstracts (lexical / concept-aware / optional embedding) or PubMed metadata
  -> claim extraction (deterministic, or optional model-backed with a citation-grounding guard)
  -> supporting / conflicting / insufficient grouping with attribution guards
  -> evidence-tier, facet, and confidence labeling with provenance spans
  -> weighted verdict aggregating support vs conflict by tier over independent sources
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

### Model-backed Extractor (optional)

`extraction.py` is the model-backed alternative the deterministic scaffold was designed to make room for. `LLMClaimExtractor` takes an injected `responder` — a real Anthropic backend (behind the `llm` extra) or an offline stand-in — and turns its raw quotes into `EvidenceClaim`s, behind two guards:

- **Citation-grounding / faithfulness guard** (always on): a quote is kept only if it is a verbatim span of the cited abstract, so a hallucinated or altered quote is dropped rather than trusted. A model can be swapped in for stance judgment without weakening the card's provenance guarantee.
- **Attribution guard** (`guard=True`, the hybrid path, default): the deterministic entity-grounding and outcome-polarity checks are re-applied on top of the model's stance, demoting a proposed `supports`/`conflicts` to `insufficient` when the quote does not name the claim's principal entity or describes the opposite outcome. Guards only demote, never promote.

The deterministic extractor remains the default. On the toy stance benchmark the hybrid guard is what makes the model-backed path safe: an unguarded naive responder leaks every cross-entity/polarity case (guardrail 3/3, macro-F1 0.444), while the same responder under the hybrid guard leaks none (0/3, macro-F1 1.000) — faithfulness is 1.000 either way.

### Quantitative Extractor

`quant.py` lifts quantitative pharmacology parameters out of prose into structured records: potency (IC50, EC50, Ki, Kd) and PK/exposure (Cmax, AUC, half-life, clearance, bioavailability), each with relation, value, unit, and a provenance span. Each measurement is attributed to the nearest preceding compound so values are comparable across compounds and assays.

### Target Dossier

`dossier.py` pivots the whole workflow from a claim to a **target**. `build_target_dossier` normalizes the target string to a concept, matches records by concept identity (not surface text), and rolls up, across every matching record: **modulators** (ontology-declared targets plus co-mentioned specific drugs, each with any extracted potency/PK values), **disease contexts**, **evidence angles** (facets), and **study tiers**. It is the entity-normalization backbone made queryable — the same concept ids that ground attribution now drive a target-centric roll-up, and it generalizes across domains (an EGFR dossier and a β2-adrenergic-receptor dossier build the same way). Reached with `--target`.

For each disease context the target appears in, the dossier also grades **target–indication validation**: a synthesized association claim is retrieved, extracted, and scored through the same claim pipeline, so every indication carries the tier-weighted [Verdict](#verdict) used for a standalone claim (e.g. EGFR/NSCLC → `well-supported`, BRAF/melanoma → `contested`). This is verdict × dossier — the meta-integration made per-indication rather than per-claim.

### Verdict

`assess_verdict` in `evidence.py` aggregates the on-claim evidence into a single graded bottom line. Support and conflict are summed as **tier weights over independent sources** — each record counts once per stance, so many sentences from one weak study cannot outvote a single strong one, and an in-vitro result cannot bury a clinical contradiction. The net balance in `[-1, 1]` maps to `well-supported`, `mixed`, `contested` (substantial evidence on both sides), or `insufficient` (too little tier-weighted evidence to call a direction — e.g. an in-silico-only claim). The per-tier breakdown is shown alongside the label so the grade is auditable rather than a black-box score.

### Evidence Card

The evidence card is the primary output object. It leads with the verdict, then contains the query or claim, retrieved records, stance-grouped sentences with facet/tier/confidence/provenance, an "Evidence by Angle" facet view, a "Quantitative Evidence" comparison, limitations, and next checks.

### Evaluation

`evaluation.py` scores the pipeline on four separated targets, so a change to one stage does not hide a regression in another:

- **Entity linking:** set-level precision/recall/F1 of concept resolution, with negative controls (`data/evaluation_entities.jsonl`).
- **Retrieval:** Recall@k and MRR with a lexical / +concept / +embedding ablation (`data/evaluation_claims.jsonl`).
- **Stance:** per-class precision/recall/F1 plus guardrail metrics — cross-entity and opposite-polarity leaks, target zero (`data/evaluation_stances.jsonl`).
- **Quantitative:** precision/recall/F1 on extracted (parameter, value, unit) tuples, with a negative control (`data/evaluation_quant.jsonl`).
- **Verdict:** label accuracy of the weighted verdict against gold, including a negative-control claim that must land on `insufficient` (`data/evaluation_verdicts.jsonl`).
- **Extractor:** deterministic vs model-backed stance macro-F1, plus a **faithfulness rate** (fraction of a responder's proposed quotes that are verbatim in the source). The faithfulness metric is what a real model backend must be held to; the offline stand-in is faithful by construction and underperforms the deterministic guards on stance, which the ablation makes explicit.

Run it with `python -m biomedical_evidence_agent.evaluation`.

## Data Policy

All bundled data in this repository is toy/sample text, and the ontology xref ids are illustrative. Optional PubMed mode uses public metadata only. The project is not copied from proprietary work, is not clinical decision support, and should not be treated as biomedical ground truth.
