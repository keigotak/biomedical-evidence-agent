<!-- Snapshot from scripts/eval_llm_ablation.py against the real API
     (claude-opus-4-8). Numbers are a live-model run on the n=3 stance
     benchmark; the model is stochastic and n is small, so treat these as a
     representative snapshot, not a fixed score. Re-run to refresh. -->

# Claim Extractor Ablation — real Claude (`claude-opus-4-8`)

Same stance benchmark as the offline ablation, but the LLM paths use the real
model. The hybrid guard re-applies entity-grounding + outcome-polarity on top of
Claude's stance; faithfulness is the fraction of the model's proposed quotes that
are verbatim in the source (guard-independent).

| Path | stance macro-F1 | guardrail leaks | citation faithfulness |
|---|---|---|---|
| deterministic | 1.000 | 0/3 | — |
| Claude, no guard | 0.933 | 0/2 | 1.000 (25/25) |
| Claude, hybrid guard | 0.933 | 0/2 | 1.000 (25/25) |

_15 unique model calls (memoized across the three paths)._

## What this shows (and doesn't)

The honest read differs from the offline ablation, and that's the point of
running both:

- **On a strong real model, the guards are a no-op here.** Claude proposes only
  verbatim quotes (faithfulness 1.000, 25/25 — nothing for the faithfulness guard
  to reject) and produces no cross-entity / polarity leaks even *without* the
  hybrid guard, so guarded and unguarded score identically.
- **The guards' value is visible on a weak extractor, not this one.** The offline
  mock responder (see the main eval) leaks every guardrail case unguarded
  (macro-F1 0.444, 3/3 leaks) and is rescued to 1.000 / 0 leaks by the same hybrid
  guard. That is what a guardrail should do: decisive when the extractor is naive,
  transparent when it is already careful.
- **Small n.** This benchmark is n=3 and the model is stochastic; Claude differing
  from the hand-written gold on one case (0.933) is within noise. The result is a
  representative snapshot, not a capability claim.
