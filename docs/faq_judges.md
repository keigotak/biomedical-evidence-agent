# Anticipated questions — judge & Q&A prep

Sharp, honest answers to the questions a serious reviewer is most likely to ask.
Each answer leads with the one-sentence version, then the backup. Points to the
artifact that proves it wherever one exists.

---

### "Isn't this just RAG / a search engine with extra steps?"

**No — it inverts the goal.** RAG retrieves passages to *produce a fluent answer*.
BioClaim Auditor retrieves to *interrogate a claim*: it returns a verdict, the
supporting **and** conflicting evidence, a verbatim-citation check, overclaim and
contradiction flags, per-entity coverage, and an explicit "what would change my
mind." The output is deliberately *not* a smooth paragraph — it's the evidence, the
disagreement, and the gaps a smooth paragraph hides.

### "Why do you need Claude? Couldn't rules do this?"

**We measured exactly this, and rules fail dangerously.** `scripts/pubmed_scan.py`
runs sixteen known claims on live PubMed two ways. On clean oncology phrasing the
deterministic rules match Claude. On messy real claims they break — in **three**
rows grading a debunked claim (*beta-carotene prevents lung cancer*, *vitamin C
prevents colds*, *arthroscopic knee surgery beats placebo*) as **well-supported**,
the opposite of the literature. Claude reads the abstracts and lands all three on
**contradicted**, and it *rescues* claims the rules missed (finding the STEP
evidence for *semaglutide reduces body weight*). It also doesn't bluff: where the
retrieved abstracts were thin (*statins reduce cardiovascular events*) it returned
`insufficient` rather than inventing support. The figure is `docs/scan_shift.svg`;
the snapshot is `outputs/example_pubmed_scan.md`. That's the case for Claude —
quantified, not asserted.

### "If Claude extracts the evidence, how do I know it isn't hallucinating?"

**Every quote is re-checked to be a verbatim span of its source.** The
citation-faithfulness guard drops any quote that isn't literally present in the
cited abstract — including quotes in the Claude reviewer's own critique. The model
is used to *read and judge*, never as the final word on whether a citation exists.
An ablation (`scripts/eval_llm_ablation.py`) shows the guard rescues a naive
extractor and stays transparent for a careful one.

### "Is this giving medical advice?"

**No, and that boundary is enforced in the output.** Every report is labeled
*research signal only — not medical advice*. It audits whether a *claim* is
supported by *literature*; it never recommends a treatment for a patient. That's a
deliberate non-goal, not an oversight.

### "It's toy data though, right?"

**The hero demos run on live PubMed.** `--source pubmed` pulls real abstracts; the
vitamin-D audit (`outputs/example_claim_audit_vitamin_d_pubmed.md`) grades a
widely-believed claim `contradicted` and quotes the **VITAL trial** verbatim
(`HR 0.96, 95% CI 0.88–1.06; P=0.47`). Sample data is the *default* so the whole
thing is reproducible offline and fully tested — but the design is not a toy-data
trick, and the scan proves it at ten-claim scale.

### "Does it generalize beyond oncology?"

**Yes — the grounding backbone is domain-agnostic.** Concept ids and verbatim
citations don't know what disease they're about. The same tool audits an
immunology/fibrosis claim (`outputs/example_claim_audit_il17a.md`) and a neurology
claim the same way. Three therapeutic areas, one auditor.

### "How do I trust your evaluation isn't cherry-picked?"

**It's built to *not* be perfect.** Seven capability streams, plus a stress set
reported at its true **8/9** — one case is a known cross-sentence limitation we
left in and documented rather than curate away. When we fix a limit, we add a
harder frontier case, so the score never rounds up to N/N. See `docs/evaluation.md`.

### "What's the honest limitation / what would you do with more time?"

**Retrieval breadth and the long tail of phrasing.** Today it reads abstracts, not
full text or trial registries, and the deterministic path still misses unusual
phrasings (which is exactly why the Claude path exists). Next: broaden the claim
scan, add full-text and registry sources, and surface the per-entity evidence map
in the UI.

### "What's actually novel here?"

**The audit framing plus the grounding guarantees.** Not "ask the model," but
"force the model to expose evidence, uncertainty, contradiction, citation
faithfulness, and next checks" — with a verbatim-span guard that makes a fabricated
citation structurally impossible, and a *measured* demonstration of where a model
is essential and where rules suffice.

### "Can I run it right now?"

**Yes, zero setup.** `python -m biomedical_evidence_agent.cli --claim "…" --report
claim-audit` runs offline on sample data. Add `--source pubmed` for live abstracts,
`--extractor llm --reviewer claude` for the Claude path (needs a key). The whole
3-minute demo runs from `bash scripts/demo.sh` with no network and no key.
