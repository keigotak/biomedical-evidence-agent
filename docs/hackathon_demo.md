# 2-minute demo script

**Product:** BioClaim Auditor — a Claude-powered claim-auditing tool for life
sciences researchers. Repo: `biomedical-evidence-agent`.

## The hook (15s)

"I'm a drug-discovery researcher — I read biomedical papers all day. Ask any LLM
'does BRAF V600E melanoma respond to targeted inhibitors?' and you get a confident
paragraph. But is it *true*, and how would you check? So I built BioClaim Auditor.
It doesn't answer the question — it audits the claim."

## Demo 0 — the real test: live PubMed (40s)  ← lead with this

```bash
python -m biomedical_evidence_agent.cli --source pubmed \
  --claim "Vitamin D supplementation reduces the risk of cancer." \
  --top-k 6 --report claim-audit --extractor llm --reviewer claude
```

(Or open `outputs/example_claim_audit_vitamin_d_pubmed.md` — a saved snapshot.)

Point at:
- **Audit Verdict: contradicted** — a claim many people believe, and the real
  literature pushes back.
- The **VITAL trial**, quoted **verbatim** (`HR 0.96, 95% CI 0.88–1.06; P=0.47`).
- **Reviewer Critique (Claude)** — catches a nuance the rules missed: cancer
  *incidence* (null) vs *mortality* (possible benefit), and names the **D-Health
  trial** next. Every quote re-grounded.

"Real PubMed, real trials, Claude reading messy abstracts — not toy data."

## Demo 1 — a contested claim, mechanics up close (30s)

```bash
python -m biomedical_evidence_agent.cli \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 3 --report claim-audit --reviewer mock
```

Point at:
- **Audit Verdict: contested** — one clinical source supports, one conflicts.
- **Citation Audit: 2/2 verbatim** — every quote is a real span of its source.
- **Contradiction Flag** — the tool refuses to call it settled.
- **Reviewer Critique** — "sources disagree; search the weaker side before concluding."
- **What Would Change My Mind** — an independent tie-breaking study.

"Instead of a smooth answer, it exposes the conflict."

## Demo 2 — an overclaim (30s)

```bash
python -m biomedical_evidence_agent.cli \
  --claim "TP53 mutation definitively cures colorectal cancer with salbutamol." \
  --top-k 3 --report claim-audit --reviewer mock
```

Point at:
- **Overclaim Flag** — `cures`, `definitively` against an `insufficient` verdict.
- **Retrieval Gap** — no direct evidence found.

"It catches the language outrunning the evidence."

## Demo 3 — the JSON artifact + Claude reviewer (20s)

```bash
python -m biomedical_evidence_agent.cli --claim "..." --report claim-audit --json
```

"Every report is also machine-readable JSON, and the reviewer can run on Claude
(`--reviewer claude`) — but even then, every quote it cites is re-checked against
the source, so it can't hallucinate a citation."

## Demo 3.5 — it works on real PubMed, not just toy data (25s)

```bash
python -m biomedical_evidence_agent.cli --source pubmed \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 5 --report claim-audit --reviewer mock
```

"Same tool, live PubMed. It pulls real abstracts and returns **well-supported**
with verbatim quotes from actual trials — FDA-approved BRAF/MEK combinations —
each citation checked against its source. The grounding isn't a toy-data trick."

## Demo 4 — it generalizes beyond oncology (20s)

```bash
python -m biomedical_evidence_agent.cli \
  --claim "IL-17A blockade may reduce fibrosis progression in systemic sclerosis." \
  --top-k 3 --report claim-audit --reviewer mock
```

"Same tool, a totally different area — immunology and fibrosis. It finds one
supporting and one conflicting clinical source and calls it **contested**. The
grounding backbone (concept ids, verbatim citations) is domain-agnostic — swap in
`TREM2 is associated with Alzheimer's disease progression.` and neurology audits
the same way. Three therapeutic areas, one auditor."

## The close (15s)

"I built a claim-auditing layer for life sciences research. Instead of asking
Claude to produce a smooth answer, it forces the model to expose evidence,
uncertainty, contradictions, citation faithfulness, and next checks. Grounded end
to end, on toy data today, and the same design points at PubMed."

## If asked about depth

- 61 tests, a 7-stream evaluation suite (entity linking, retrieval, stance +
  guardrails, quantitative, MoA, verdict, dossier), all grounded on concept ids.
- Experiments folder (hypothesis stress test, reviewer duel idea) is isolated so
  it can't break the main demo.
