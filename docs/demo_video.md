# 3-minute demo video — storyboard & script

A shot-by-shot plan for a ~3:00 screen-recording. Every command is copy-paste
and produces the output described (verified). The terminal path needs no Docker
or API key; two beats are richer if you can show the Streamlit UI and a
Claude-backed run, but both have a no-setup fallback.

**Before recording:** big terminal font, `cd` into the repo, and pre-clear the
screen. Optional: `docker compose up --build` in a second window for the UI beat.

---

## 0:00–0:15 — Hook

**On screen:** the README top (the hero image) or a title card "BioClaim Auditor".

> "Ask an LLM whether BRAF V600E melanoma responds to targeted inhibitors and you
> get a confident paragraph. But is it *true* — and how would you check? BioClaim
> Auditor doesn't answer the question. It **audits the claim.**"

---

## 0:15–1:00 — Demo 1: the contested claim (the core)

**On screen:** run it, scroll slowly through the report.

```bash
python -m biomedical_evidence_agent.cli \
  --claim "BRAF V600E melanoma is associated with response to targeted inhibitor treatment." \
  --top-k 3 --report claim-audit --reviewer mock
```

Point the cursor at, in order: **Audit Verdict: contested** → **Supporting** vs
**Conflicting Evidence** → **Citation Audit 2/2 verbatim** → **Contradiction
flag** → **What Would Change My Mind**.

> "It grades the claim **contested** — one clinical study supports it, another
> conflicts. Every cited quote is verified to be a **verbatim span** of its
> source. It **flags the contradiction** instead of smoothing it over — and tells
> you exactly what evidence would break the tie."

*(Richer option: show the same claim in the Streamlit UI — the verdict badge, the
colored Evidence Map bars, the downloadable report.)*

---

## 1:00–1:30 — Demo 2: catching an overclaim

```bash
python -m biomedical_evidence_agent.cli \
  --claim "TP53 mutation definitively cures colorectal cancer with salbutamol." \
  --top-k 3 --report claim-audit
```

Point at: **🔴 Overclaim flag** (`cures`, `definitively` vs an `insufficient`
verdict) and the **Evidence Map** line `colorectal cancer … ⚠ no evidence
addresses this entity`.

> "Feed it a claim whose language outruns the evidence — *definitively cures* —
> and it fires an **overclaim** flag. Its Evidence Map breaks the claim down by
> entity and shows that **colorectal cancer is addressed by nothing** retrieved.
> It won't let the wording slide."

---

## 1:30–2:00 — Generalization + real literature

**On screen:** the comparison table, then the PubMed snapshot.

```bash
python experiments/compare_claims.py
```

> "Same tool across **oncology, immunology, and neurology** — three areas, one
> auditor: two contested, one well-supported, one overclaim, at a glance."

Then open [`outputs/example_claim_audit_pubmed.md`](../outputs/example_claim_audit_pubmed.md)
(or run `--source pubmed` live if the network is up):

> "And it's not toy-only. Point it at **live PubMed** and it audits real papers —
> well-supported, with verbatim quotes from actual trials."

---

## 2:00–2:35 — Built with Claude

**On screen:** open [`outputs/example_claim_audit_claude_reviewer.md`](../outputs/example_claim_audit_claude_reviewer.md)
(or run `--reviewer claude` with a key). Highlight the BRIM-3 line.

> "The reviewer is **Claude itself**, re-reading the card as a skeptic. Here it
> flags the hedged wording, distinguishes *durable* from *initial* response, and
> points to the pivotal **BRIM-3 trial** as the next source. And every quote
> Claude cites is **re-checked against the source** — so it can't hallucinate a
> citation. Notice its BRIM-3 suggestion carries no quote, because that trial
> isn't in the corpus."

*(Optional flourish: `experiments/reviewer_duel.py --mode claude` — an advocate,
a skeptic, and a judge, all grounded.)*

---

## 2:35–3:00 — Close: honesty + the pitch

**On screen:** the tail of `python -m biomedical_evidence_agent.evaluation`
(stress 8/9, the extractor ablation) or [`docs/evaluation.md`](evaluation.md),
then a safety card.

> "It's honest about its limits: a **7-stream evaluation**, a stress set reported
> at its true **8 of 9**, and an ablation showing the citation guard **rescues a
> naive extractor and stays transparent for a careful one**. The pitch: instead
> of asking Claude for a smooth answer, BioClaim Auditor forces the model to
> expose **evidence, uncertainty, contradictions, citation faithfulness, and next
> checks.** Research signal only — no medical advice."

---

## Shortest zero-setup path (if you only have a terminal)

1. Demo 1 command → 2. Demo 2 command → 3. `compare_claims.py` → 4. open the
PubMed and Claude-reviewer snapshots in `outputs/` → 5. `… .evaluation | tail`.
That is the full 3 minutes with no Docker and no API key.

## Timing cheat-sheet

| Beat | Time | Shows |
|---|---|---|
| Hook | 0:15 | what it is / isn't |
| Contested claim | 0:45 | verdict, citations, contradiction, WWCMM |
| Overclaim | 0:30 | overclaim flag + entity coverage gap |
| Generalization + PubMed | 0:30 | 3 areas + real papers |
| Built with Claude | 0:35 | grounded reviewer, no fabricated citation |
| Close | 0:25 | honest eval + pitch + safety |
