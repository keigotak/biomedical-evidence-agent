# Evaluation

Run everything: `python -m biomedical_evidence_agent.evaluation`.

The design goals are the ones that make an evaluation trustworthy rather than
flattering: **separate targets** (a change in one stage can't hide a regression
in another), **ablations** (show the delta a component actually buys), **negative
controls** (cases whose correct answer is "extract nothing" or "don't call it"),
and **not over-claiming on small n**. This page is deliberately honest about where
the numbers are strong signal and where they are not.

## Capability streams

| Stream | n (cases) | Metric | Negative control | Reading |
|---|---|---|---|---|
| Entity linking | 8 | set P/R/F1 | yes (`el-007`) | dictionary resolution; near-ceiling by design |
| Retrieval (ablation) | 7 | recall@k, MRR | — | **real signal**: lexical 0.571 < +concept 1.000 > +embedding 0.714 |
| Stance + guardrail | 3 (+3 guardrail) | macro-F1, leak count | yes (guardrail tags) | leaks must be 0 |
| Quantitative | 8 | P/R/F1 on (param, **relation**, value, unit) | yes (`q-003/004/005`) | relation is graded, so `<5 nM` ≠ `=5 nM` |
| Mechanism of action | 7 | P/R/F1 on (drug, target, mechanism) | yes (`moa-003/004/005`) | negation + distractor drugs covered |
| Weighted verdict | 5 | label accuracy | yes (`vd-004`) | incl. a negative control |
| Dossier indication verdict | 3 | label accuracy | yes (`dv-003`) | verdict × dossier, end to end |
| Extractor (ablation) | — | macro-F1 + faithfulness | — | **real signal**: mock-LLM no-guard 0.444 / 3 leaks → hybrid 1.000 / 0 leaks |

The two **ablation** rows carry the most information: they show a component
earning its place (the concept layer beats a general embedding on this domain
set; the hybrid guard rescues an unguarded model from 0.444 to 1.000 with zero
citation leaks). A bare "1.000" on the small extraction golds is worth much less.

## Honest caveats

- **Small n.** Most golds are single-digit; a 1.000 there is a smoke test, not a
  capability claim. Treat the ablations and the stress set (below) as the signal.
- **Circularity, partly mitigated.** Several extraction gold texts were verbatim
  corpus sentences (train == test). The quant/MoA golds now add **held-out
  paraphrases** (`q-006`, `moa-006/007`) with different surface realizations, so
  they test generalization rather than recall of their own inputs. More would
  help.
- **Negative controls are mostly "abstain" cases** plus a few adversarial
  "wrong-positive" controls (a reagent mass after a `Ki` cue, a negated value, a
  negated MoA cue) that a naive extractor gets wrong — the pipeline now abstains
  on all three.

## Stress set — the edges, reported honestly

`data/evaluation_stress.jsonl` holds deliberately hard cases and is **not expected
to be perfect**. It currently scores **8/9 handled**; the misses are documented
limitations, not regressions, and the state is pinned by a test so a future fix
has to update it:

| Case | Handled | Note |
|---|---|---|
| `ss-001` negation before a value | ✅ | abstains |
| `ss-002` distractor drug in the sentence | ✅ | not mis-paired |
| `ss-003` hyphenated morphology (`EGFR-mutated`) | ✅ | right boundary now allows a trailing hyphen (`non-EGFR` still blocked) |
| `ss-004` numeric range (`10–20 nM`) | ✅ | takes the lower (cited) bound |
| `ss-005` cue collision (`suppressed … activation`) | ✅ | nearest-to-drug cue wins (antagonist) |
| `ss-006` qualifying hyphen prefix (`anti-EGFR`) | ✅ | anti-/pan- link; only negating non-/un- stay blocked |
| `ss-007` scientific notation (ASCII `1.2 x 10^-9`) | ✅ | computed as mantissa × 10^exp |
| `ss-008` Unicode superscript (`1.2 × 10⁻⁹`) | ✅ | superscript exponent translated |
| `ss-009` cross-sentence attribution | ❌ (by design) | extraction is per-sentence to keep attribution local and auditable |

The one open row is an **intentional** boundary (per-sentence extraction keeps every attribution local and auditable), not an unhandled bug. Each is a concrete, reproducible failure with a
one-line cause — the point of the stress set is to name them rather than let a
curated 1.000 imply they don't exist.
