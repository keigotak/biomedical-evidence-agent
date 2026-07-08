# 2-minute demo script

**Product:** BioClaim Auditor — a Claude-powered claim-auditing tool for life
sciences researchers. Repo: `biomedical-evidence-agent`.

## The hook (15s)

"Ask any LLM 'does BRAF V600E melanoma respond to targeted inhibitors?' and you
get a confident paragraph. But is it *true*, and how would you check? BioClaim
Auditor doesn't answer the question — it audits the claim."

## Demo 1 — a contested claim (40s)

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
