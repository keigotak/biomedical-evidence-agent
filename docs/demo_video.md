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

> "I'm a drug-discovery researcher, and I read biomedical papers all day. Ask an
> LLM whether BRAF V600E melanoma responds to targeted inhibitors and you get a
> confident paragraph — but is it *true*, and how would you check? So I built
> BioClaim Auditor. It doesn't answer the question. It **audits the claim.**"

---

## 0:15–0:55 — Demo 1: the contested claim (the core)

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

## 0:55–1:20 — Demo 2: catching an overclaim

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

## 1:20–2:05 — The real test: live PubMed (the hero) + scale figure

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
> null result, quoted **verbatim**. This is real literature, not toy data."

**On screen:** now full-screen [`docs/scan_shift.svg`](scan_shift.svg) (the figure
under the README scale callout — hold it for 8–10s).

> "And it's not a one-off. Here are **ten well-known claims** audited on live
> PubMed at once. The hollow ring is the offline deterministic rules; the filled
> dot is **Claude**. On established oncology they agree — but on messy real claims
> the rules break: they grade *beta-carotene prevents lung cancer* and *vitamin C
> prevents colds* as **well-supported**, the exact opposite of the truth. Claude
> reads the abstracts and pulls both to **contradicted**. That's what 'Built with
> Claude' buys here — a **measurable** difference, not a gimmick."

---

## 2:05–2:35 — Built with Claude: expert-level review

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

1. Demo 1 command → 2. Demo 2 command → 3. open the PubMed / Claude-reviewer
snapshots in `outputs/` → 4. open `docs/scan_shift.svg` (the 10-claim figure) →
5. `… .evaluation | tail`. That is the full 3 minutes with no Docker and no API key.

## Timing cheat-sheet

| Beat | Time | Shows |
|---|---|---|
| Hook | 0:15 | what it is / isn't |
| Contested claim | 0:40 | verdict, citations, contradiction, WWCMM |
| Overclaim | 0:25 | overclaim flag + entity coverage gap |
| PubMed + scale figure | 0:45 | vitamin D contradicted + 10-claim shift (Claude necessity) |
| Built with Claude | 0:30 | grounded reviewer, no fabricated citation |
| Close | 0:25 | honest eval + pitch + safety |
