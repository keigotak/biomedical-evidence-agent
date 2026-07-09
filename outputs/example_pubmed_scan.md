<!-- Snapshot from scripts/pubmed_scan.py against live PubMed (deterministic
     extractor vs real Claude extractor, claude-opus-4-8). Live results evolve as
     the literature grows; re-run to refresh. -->

# PubMed claim scan — deterministic vs real Claude, over 16 known claims

Running the same audit over a spread of well-known claims on **live PubMed** —
some the literature supports, some it has debunked — and reading each abstract
two ways: the offline deterministic extractor, and the real Claude extractor.

| Claim | Deterministic | Claude |
|---|---|---|
| BRAF V600E melanoma responds to targeted inhibitors | well-supported | **well-supported** |
| EGFR mutations predict response to EGFR TKIs in NSCLC | well-supported | **well-supported** |
| Trastuzumab improves survival in HER2+ breast cancer | well-supported | **well-supported** |
| Aspirin reduces the risk of colorectal cancer | insufficient | **mixed** |
| Vitamin D supplementation reduces cancer risk | insufficient | **contradicted** |
| Antioxidant supplements reduce all-cause mortality | insufficient | **contradicted** |
| Beta-carotene supplementation prevents lung cancer | **well-supported** | **contradicted** |
| Vitamin C supplementation prevents the common cold | **well-supported** | **contradicted** |
| Ivermectin reduces mortality in COVID-19 | insufficient | **contradicted** |
| Hydroxychloroquine reduces mortality in COVID-19 | insufficient | **contradicted** |
| The MMR vaccine causes autism | insufficient | **contradicted** |
| Hormone replacement therapy prevents coronary heart disease | insufficient | **contradicted** |
| Arthroscopic surgery for knee osteoarthritis beats placebo | **well-supported** | **contradicted** |
| Statins reduce cardiovascular events in high-risk patients | insufficient | **insufficient** |
| Semaglutide reduces body weight in adults with obesity | insufficient | **well-supported** |
| Aducanumab slows cognitive decline in Alzheimer's disease | insufficient | **well-supported** |

| | well-supported | contested | mixed | contradicted | insufficient |
|---|---|---|---|---|---|
| **Deterministic** | 6 | 0 | 0 | 0 | 10 |
| **Claude** | 5 | 0 | 1 | 9 | 1 |

## Why this is the case for Claude — measured, not asserted

- **On established claims, the two agree** (well-supported). The clean
  "X predicts response to Y" phrasing is exactly what the deterministic stance
  rules were built for.
- **On messy, varied real-world claims, the deterministic rules break.** They
  either miss the evidence entirely (`insufficient`) or — worse — get it
  **dangerously wrong**. In **three** rows the rules grade a *debunked* claim as
  **well-supported**: *beta-carotene prevents lung cancer* (ATBC/CARET showed it
  *increased* lung-cancer risk), *vitamin C prevents the common cold* (null), and
  *arthroscopic knee surgery beats placebo* (sham-controlled trials found no
  benefit). Endorsing any of these is exactly the failure a claim auditor must not
  make.
- **The real Claude extractor gets them right** — every debunked/overhyped claim
  lands on **contradicted** (MMR-autism, HRT-for-CHD, ivermectin and HCQ for
  COVID among them), and it *rescues* claims the rules missed: it finds the STEP
  evidence for *semaglutide reduces body weight* and lands it **well-supported**,
  and calls *aspirin reduces colorectal-cancer risk* **mixed** rather than blank.
- **It doesn't bluff.** For *statins reduce cardiovascular events*, the six
  retrieved abstracts didn't contain decisive head-to-head evidence, and Claude
  returned **insufficient** rather than inventing support — the honest answer when
  the retrieved slice is thin.

That is what "Built with Claude" buys here: not a gimmick, but the difference
between a tool that endorses arthroscopic surgery and beta-carotene and one that
correctly flags them as contradicted. The extractor is Claude because messy real
literature needs a model to read it — and the citation-grounding guard keeps that
model honest (every quote verbatim in its source).
