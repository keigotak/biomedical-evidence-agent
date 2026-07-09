# Submission form — Built with Claude: Life Sciences

Field-by-field, ready to paste. Deadline: **Jul 13, 9:00 PM EDT**. Trim to any
per-field limit shown on the form.

---

## Team Name
**Counterscreen** — like the pharma counterscreen that filters out false-positive
hits, this team filters out false-positive *claims*. (Product name stays *BioClaim
Auditor* in the field below.)

## Team Members
Keigo Takahashi (ktak5)

## Project Name
BioClaim Auditor

## Track
**Build** — *build beyond the bench: a named life-sciences user + working software
made with Claude Code that outlasts the week.*

## Project description — what you built, what you found, why it matters

BioClaim Auditor is working software — CLI, Streamlit UI, and reproducible reports
— for a user I can name because I am one: a drug-discovery researcher who reads
biomedical papers all day and is tired of confident claims (from papers, press
releases, and now LLMs) that outrun their evidence.

It doesn't *answer* a claim — it *audits* it. Give it one biological claim; it
retrieves real papers, extracts the evidence with Claude, and returns a **Claim
Audit Report**: a graded verdict (`well-supported` → `contested` → `mixed` →
`contradicted` → `insufficient`), every quote checked to be a **verbatim span** of
its source, overclaim and contradiction flags, per-entity evidence coverage, a
Claude reviewer critique, and an explicit *"what would change my mind."*

**What I found, by measuring:** run it over 16 well-known claims on live PubMed and
you can quantify where a model is essential. Offline rules dangerously grade three
*debunked* claims — beta-carotene for lung cancer, vitamin C for colds,
arthroscopic knee surgery — as **well-supported**; Claude reads the abstracts and
correctly **contradicts** all three, while *rescuing* claims the rules missed
(semaglutide for weight loss) and declining to bluff when evidence is thin (it
leaves statins `insufficient` rather than inventing support).

**Why it matters:** the failure mode of LLMs in science is a fluent, unverifiable
answer. This inverts that — it forces the model to expose evidence, disagreement,
citation faithfulness, and next checks, with a verbatim-span guard that makes a
fabricated citation structurally impossible. Research signal only — not medical
advice.

## Link to your work
https://github.com/keigotak/biomedical-evidence-agent

*(Public. Start with the README; the live-PubMed hero, the 16-claim
deterministic-vs-Claude figure, and the honest evaluation are all linked from the
top. Runs with zero setup: `python -m biomedical_evidence_agent.cli --claim "…"
--report claim-audit`.)*

## Demo Video (≤ 3 minutes)
*(link after recording — storyboard: `docs/demo_video.md`, JA `docs/demo_video_ja.md`;
one-command driver: `bash scripts/demo.sh`)*

## How did you use Claude? Which products, and where did they matter most?

Two ways, and both were central.

**Claude Code** built the entire tool in a week — the concept-grounded retrieval
and audit pipeline, the evaluation harness (83 tests, a 7-stream capability suite
plus ablations and an honest stress set), the Streamlit UI, and the reproducible
figures — iterating test-first with real end-to-end behavior checks, not just green
tests.

**The Claude API (Opus 4.8)** is the product's engine: the evidence **extractor**
that reads messy PubMed abstracts into grounded stance, and the **reviewer** that
critiques each audit. This is where Claude mattered most, and I can prove it: the
16-claim live-PubMed scan (`scripts/pubmed_scan.py`, figure `docs/scan_shift.svg`)
shows deterministic rules mislabeling debunked claims as well-supported while
Claude gets them right — a measured difference, not a gimmick. A verbatim-span
guard re-checks every quote Claude cites, so the model's judgment is used without
ever letting it hallucinate a citation.

## Thoughts / feedback on building with Claude (Science)

Honest note: this is a **Build-track** project, so I built with **Claude Code** and
the **Claude API**, not Claude Science. Feedback from that experience: Claude Code
was strongest when I made it *verify behavior*, not just pass tests — driving the
real CLI/UI and reading actual outputs caught bugs a green test suite hid (e.g. a
drug-class grounding leak an adversarial review agent found). The structured-output
JSON-schema path on Opus 4.8 made the in-product extractor reliable enough to
depend on. If Claude Science exposes the same literature + grounding primitives as
callable tools, a claim auditor like this would slot in naturally as a verification
layer over its answers.
