// Mirrors the payload produced by `audit_json` in report.py, plus the extra
// fields the API layer (api.py::run_audit) attaches (markdown, settings, ...).

export type VerdictLabel =
  | "well-supported"
  | "mixed"
  | "contested"
  | "contradicted"
  | "insufficient";

export interface Verdict {
  label: VerdictLabel | string;
  strength: number;
  support_sources: number;
  conflict_sources: number;
  indirect_sentences: number;
  rationale: string;
}

export interface EvidenceClaim {
  source_id: string;
  text: string;
  tier: string;
  confidence: string;
  span: [number, number];
}

export interface EvidenceGroups {
  supporting: EvidenceClaim[];
  conflicting: EvidenceClaim[];
  indirect: EvidenceClaim[];
}

export interface CitationAudit {
  checked: number;
  verbatim: number;
  faithfulness: number;
}

export interface EvidenceMapEntry {
  name: string;
  type: string;
  supports: number;
  conflicts: number;
  indirect: number;
  sources: string[];
}

export interface AuditFlag {
  category: string;
  severity: "high" | "warn" | "info" | string;
  message: string;
  detail: string;
}

export interface ReviewFinding {
  kind: string;
  note: string;
  source_id: string;
  quote: string;
}

export interface ReviewerCritique {
  reviewer: string;
  assessment: string;
  findings: ReviewFinding[];
}

export interface AuditResult {
  claim: string;
  source: string;
  verdict: Verdict | null;
  evidence: EvidenceGroups;
  citation_audit: CitationAudit;
  evidence_map: EvidenceMapEntry[];
  flags: AuditFlag[];
  reviewer_critique: ReviewerCritique | null;
  what_would_change_my_mind: string[];
  next_checks: string[];
  limitations: string[];
  markdown: string;
  reviewer_warning: string | null;
  settings: {
    source: string;
    retriever: string;
    top_k: number;
    reviewer: string;
  };
}

export interface AuditParams {
  claim: string;
  source: string;
  retriever: string;
  top_k: number;
  reviewer: string;
}
