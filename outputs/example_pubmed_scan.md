<!-- Snapshot from scripts/pubmed_scan.py against live PubMed (deterministic
     extractor vs real Claude extractor, claude-opus-4-8). Live results evolve as
     the literature grows; re-run to refresh. -->

# PubMed claim scan — deterministic vs real Claude, over 10 known claims

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

| | well-supported | contested | mixed | contradicted | insufficient |
|---|---|---|---|---|---|
| **Deterministic** | 5 | 0 | 0 | 0 | 5 |
| **Claude** | 3 | 0 | 1 | 6 | 0 |

## Why this is the case for Claude — measured, not asserted

- **On established oncology claims, the two agree** (well-supported). The clean
  "X predicts response to Y" phrasing is exactly what the deterministic stance
  rules were built for.
- **On messy, varied real-world claims, the deterministic rules break.** They
  either miss the evidence entirely (`insufficient`) or — worse — get it
  **dangerously wrong**: they grade *beta-carotene prevents lung cancer* and
  *vitamin C prevents the common cold* as **well-supported**, when the literature
  (ATBC/CARET showed beta-carotene *increased* lung-cancer risk; cold-prevention
  trials are null) says the opposite.
- **The real Claude extractor gets them right** — every debunked/overhyped claim
  lands on **contradicted**, and the established ones stay **well-supported**. A
  sensible distribution across real literature.

That is what "Built with Claude" buys here: not a gimmick, but the difference
between a tool that endorses beta-carotene for lung cancer and one that correctly
flags it as contradicted. The extractor is Claude because messy real literature
needs a model to read it — and the citation-grounding guard keeps that model
honest (every quote verbatim in its source).
