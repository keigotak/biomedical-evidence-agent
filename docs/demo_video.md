# 3-minute demo video — storyboard & script

A shot-by-shot plan for a ~3:00 screen-recording. Every command is copy-paste
and produces the output described (verified). The terminal path needs no Docker
or API key; two beats are richer if you can show the Streamlit UI and a
Claude-backed run, but both have a no-setup fallback.

**Before recording:** big terminal font, `cd` into the repo, and pre-clear the
screen. Optional: `docker compose up --build` in a second window for the UI beat.

**Easiest path — one command, paced by you:**

```bash
bash scripts/demo.sh        # runs all six beats; press enter between each while you narrate
```

`scripts/demo.sh` prints a header for each beat, runs the exact command below,
and waits for enter — so you never type on camera, and the PubMed and Claude
beats read saved snapshots (no network, no API key). The script and this
storyboard stay in lock-step. The rest of this file is the narration and what to
point at.

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

## 1:30–2:05 — The real test: live PubMed (the hero)

**On screen:** a quick flash of the 3-domain comparison table, then the vitamin D
audit — the snapshot [`outputs/example_claim_audit_vitamin_d_pubmed.md`](../outputs/example_claim_audit_vitamin_d_pubmed.md)
(or run it live with a key):

```bash
python -m biomedical_evidence_agent.cli --source pubmed \
  --claim "Vitamin D supplementation reduces the risk of cancer." \
  --top-k 6 --report claim-audit --extractor llm --reviewer claude
```

Point at: **Audit Verdict: contradicted** and the **VITAL** conflicting line
(`hazard ratio, 0.96, 95% CI 0.88–1.06; P=0.47`).

> "Same tool across three areas — but here's the real test: point it at **live
> PubMed**. *Vitamin D reduces cancer risk* — a claim a lot of people believe. The
> auditor grades it **contradicted**, and pulls the landmark **VITAL trial's**
> null result, quoted **verbatim**. This is real literature, not toy data — and
> Claude does the extraction from messy real abstracts."

---

## 2:05–2:40 — Built with Claude: expert-level review

**On screen:** the Reviewer Critique section of the same vitamin D snapshot.

> "And the reviewer is **Claude**, reading the same evidence as an expert. It
> agrees the claim is contradicted for cancer *incidence* — but catches a nuance
> the rules missed: cancer *mortality* may actually benefit, and one source was
> mislabeled. It even names the next trial to pull — the **D-Health trial**. And
> every quote it cites is **re-checked against the source**, so it can't fabricate
> a citation."

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
