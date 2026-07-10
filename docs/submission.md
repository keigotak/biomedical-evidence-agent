# Submission copy

Ready-to-paste text for the hackathon submission form. Field names vary between
platforms, so this file has one main description plus short, reusable answers for
the fields that usually appear. Trim to each form's word limit.

---

## One-line tagline

> BioClaim Auditor — it doesn't answer a biomedical claim, it audits it: verdict,
> verbatim citations, contradictions, and what would change its mind.

## Elevator pitch (≈40 words)

> Ask any LLM "does vitamin D reduce cancer risk?" and you get a confident
> paragraph. BioClaim Auditor instead reads the real literature, grades the claim,
> quotes the trials **verbatim**, flags contradictions, and says what evidence
> would change its mind.

## Main description (≈250 words)

> **The problem.** Researchers and clinicians are drowning in confident,
> unverifiable claims — from papers, press releases, and now LLMs. A smooth answer
> is the *last* thing you want when the question is "is this actually true, and how
> would I check?"
>
> **What it does.** BioClaim Auditor is a claim-auditing tool for life-sciences
> evidence. Give it a claim; it retrieves real papers, extracts the evidence, and
> returns a **Claim Audit Report**: a verdict (`well-supported` → `contested` →
> `mixed` → `contradicted` → `insufficient`), every quote checked to be a
> **verbatim span of its source**, flags for overclaiming and contradiction,
> per-entity evidence coverage, and an explicit *"what would change my mind."*
>
> **Why Claude.** The extractor is Claude, and we *measure* why: over sixteen known
> claims on live PubMed, offline rules either miss the evidence or get it
> dangerously wrong — in three rows grading a debunked claim (beta-carotene for lung
> cancer, vitamin C for colds, arthroscopic knee surgery) as well-supported. Claude
> reads the messy abstracts and correctly lands all three `contradicted`, while
> rescuing claims the rules missed. A Claude reviewer then critiques the audit — and
> every quote it cites is re-grounded, so it cannot fabricate a citation.
>
> **Honesty as a feature.** A 7-stream evaluation, a stress set reported at its
> true 8/9 (never curated to a perfect score), and ablations showing the citation
> guard rescues a naive extractor. Research signal only — not medical advice.

## Why Claude / how the model is used (≈60 words)

> Claude is the evidence extractor and the reviewer. The scan in
> `scripts/pubmed_scan.py` quantifies the difference over sixteen live-PubMed
> claims: deterministic rules mislabel three debunked claims as well-supported,
> while Claude lands them `contradicted` and rescues ones the rules missed (see
> `docs/scan_shift.svg`). A verbatim-span guard re-checks every quote Claude cites,
> so the model exposes evidence without being able to hallucinate a citation.

## Technical depth (≈70 words)

> Stdlib-only core: ontology concept-normalization, concept-aware retrieval, stance
> classification with entity-grounding and outcome-polarity guards, tier-weighted
> verdicts, citation-faithfulness and overclaim/contradiction auditing, MoA and
> quantitative extraction. Claude backends are dependency-injected and optional, so
> the whole pipeline runs and is fully tested offline (83 tests, 7 evaluation
> streams). Live PubMed retrieval, a React + FastAPI web UI, and reproducible SVG
> figures ship alongside.

## What's next (≈40 words)

> Broaden the claim scan, add trial-registry and full-text sources, and surface the
> per-entity evidence map in the UI. The grounding backbone (concept ids, verbatim
> citations) is domain-agnostic — it already audits oncology, immunology, and
> neurology claims the same way.

## Links to include

- Repo: `https://github.com/keigotak/biomedical-evidence-agent`
- Hero figure: `docs/hero.svg` · Scale figure: `docs/scan_shift.svg`
- Real-PubMed snapshots: `outputs/example_claim_audit_vitamin_d_pubmed.md`,
  `outputs/example_pubmed_scan.md`
- Evaluation writeup: `docs/evaluation.md`
- Demo storyboard: `docs/demo_video.md` (JA: `docs/demo_video_ja.md`)
