import type { AuditParams } from "../types";
import { REVIEWERS, RETRIEVERS, SOURCES } from "../constants";

interface Props {
  params: AuditParams;
  onChange: (patch: Partial<AuditParams>) => void;
  examples: string[];
  onPickExample: (claim: string) => void;
  disabled: boolean;
  open: boolean;
  onClose: () => void;
}

export function Sidebar({
  params,
  onChange,
  examples,
  onPickExample,
  disabled,
  open,
  onClose,
}: Props) {
  const pubmed = params.source === "pubmed";
  return (
    <aside className={open ? "sidebar open" : "sidebar"}>
      <div>
        <div className="brand">
          <span className="logo">🔬</span>
          <span>BioClaim Auditor</span>
          <button
            className="sidebar-close"
            aria-label="Close menu"
            onClick={onClose}
          >
            ✕
          </button>
        </div>
        <div className="brand-sub">Life-sciences evidence auditing</div>
      </div>

      <div className="field">
        <span className="field-label">Source</span>
        <div className="segmented" role="group" aria-label="Source">
          {SOURCES.map((s) => (
            <button
              key={s}
              aria-pressed={params.source === s}
              disabled={disabled}
              onClick={() => onChange({ source: s })}
            >
              {s}
            </button>
          ))}
        </div>
        <span className="field-help">
          {pubmed ? "Live PubMed metadata (public)." : "Bundled sample corpus."}
        </span>
      </div>

      <div className="field">
        <span className="field-label">Retriever</span>
        <select
          value={params.retriever}
          disabled={disabled || pubmed}
          onChange={(e) => onChange({ retriever: e.target.value })}
        >
          {RETRIEVERS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        {pubmed && <span className="field-help">PubMed uses its own ranking.</span>}
      </div>

      <div className="field">
        <span className="field-label">Records retrieved (top-k)</span>
        <div className="slider-row">
          <input
            type="range"
            min={1}
            max={10}
            value={params.top_k}
            disabled={disabled}
            onChange={(e) => onChange({ top_k: Number(e.target.value) })}
          />
          <span className="slider-val">{params.top_k}</span>
        </div>
      </div>

      <div className="field">
        <span className="field-label">Reviewer</span>
        <select
          value={params.reviewer}
          disabled={disabled}
          onChange={(e) => onChange({ reviewer: e.target.value })}
        >
          {REVIEWERS.map((r) => (
            <option key={r} value={r}>
              {r}
            </option>
          ))}
        </select>
        <span className="field-help">
          'claude' needs the llm extra + ANTHROPIC_API_KEY.
        </span>
      </div>

      <div className="field">
        <span className="field-label">Example claims</span>
        <div className="examples">
          {examples.map((ex, i) => (
            <button
              key={i}
              className="example-btn"
              disabled={disabled}
              onClick={() => onPickExample(ex)}
            >
              {ex}
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-footer">
        Research signal only — not medical advice, no patient data. Toy / sample
        data by default.
      </div>
    </aside>
  );
}
