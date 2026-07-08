# What makes BioClaim Auditor different

Most "ask an LLM about a paper" tools optimize for a **smooth answer**. BioClaim
Auditor optimizes for a **reviewable audit**. The difference is the whole point.

## It is not a literature search engine

You do not give it a topic and get a summary. You give it one specific
biological or translational **claim**, and it audits that claim against retrieved
evidence. The unit of work is a proposition that can be supported, contradicted,
or left unproven — not a query.

## It exposes what a smooth answer hides

For a claim, a chat model will usually produce a fluent paragraph. BioClaim
Auditor instead forces five things into the open:

1. **Supporting vs conflicting evidence** — grouped, per independent source, with
   a tier-weighted verdict (`well-supported` / `mixed` / `contested` /
   `insufficient`) rather than a vibe.
2. **Citation faithfulness** — every cited sentence is verified to be a *verbatim*
   span of its source. A quote that is not is flagged, not shown as fact. The
   reviewer agent's citations are re-checked the same way, so a critique cannot
   smuggle in a fabricated quote either.
3. **Overclaim** — assertive language (`cures`, `definitively`, `always`) that the
   evidence verdict does not earn is flagged. A `well-supported` verdict resting
   only on preclinical tiers is flagged too.
4. **Contradictions and retrieval gaps** — conflicting independent sources, no
   direct evidence, or no clinical-tier evidence are surfaced as explicit flags.
5. **What would change my mind** — concrete next evidence keyed to the current
   verdict and gaps, not generic advice.

## Grounding is the backbone, everywhere

The same concept-identity grounding runs through the whole stack: entities
normalize to concept ids, evidence attribution requires the claim's entities to
actually appear, mechanism-of-action relations require a drug's *declared*
target, and citations must be verbatim. The audit never invents support — it
only flags where the card outruns its evidence.

## The one-line pitch

> I built a claim-auditing layer for life sciences research. Instead of asking
> Claude to produce a smooth answer, it forces the model to expose evidence,
> uncertainty, contradictions, citation faithfulness, and next checks.

## What it is not

Not medical advice, not clinical decision support, not a full AI-scientist
workbench, not a wet-lab analysis tool, and not a perfect citation verifier. It
is a narrow, deep claim auditor on toy/sample data.
