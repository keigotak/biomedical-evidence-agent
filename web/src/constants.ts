// Status → visual mapping. Values are CSS custom-property references so a single
// theme definition (styles.css) drives both light and dark. Colour is always a
// secondary encoding — each mapping is paired with a label or icon in the UI.

export const VERDICT_COLOR: Record<string, string> = {
  "well-supported": "var(--good)",
  mixed: "var(--warn)",
  contested: "var(--warn)",
  contradicted: "var(--bad)",
  insufficient: "var(--neutral)",
};

export const STANCE_COLOR = {
  supports: "var(--good)",
  conflicts: "var(--warn)",
  indirect: "var(--neutral)",
  uncovered: "var(--bad)",
} as const;

export const SEVERITY: Record<
  string,
  { icon: string; bg: string; border: string; text: string }
> = {
  high: { icon: "🔴", bg: "var(--bad-soft)", border: "var(--bad)", text: "var(--bad)" },
  warn: { icon: "🟡", bg: "var(--warn-soft)", border: "var(--warn)", text: "var(--warn)" },
  info: { icon: "🟢", bg: "var(--good-soft)", border: "var(--good)", text: "var(--good)" },
};

export const SOURCES = ["sample", "pubmed"] as const;
export const RETRIEVERS = ["concept", "lexical"] as const;
export const REVIEWERS = ["mock", "none", "claude"] as const;
