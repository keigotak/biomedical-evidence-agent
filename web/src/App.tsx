import { useEffect, useState } from "react";
import { Sidebar } from "./components/Sidebar";
import { Results } from "./components/Results";
import { fetchExamples, runAudit } from "./api";
import type { AuditParams, AuditResult } from "./types";

const DEFAULT_PARAMS: AuditParams = {
  claim: "",
  source: "sample",
  retriever: "concept",
  top_k: 5,
  reviewer: "mock",
};

export default function App() {
  const [params, setParams] = useState<AuditParams>(DEFAULT_PARAMS);
  const [examples, setExamples] = useState<string[]>([]);
  const [result, setResult] = useState<AuditResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // The sidebar is an always-open column on desktop and an off-canvas drawer on
  // narrow screens. If the window grows back past the breakpoint while the
  // drawer is open, drop the open state so it doesn't linger with a backdrop.
  useEffect(() => {
    const onResize = () => {
      if (window.innerWidth > 820) setSidebarOpen(false);
    };
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  useEffect(() => {
    fetchExamples()
      .then((ex) => {
        setExamples(ex);
        // Seed the textarea with the first example so the app is one click away
        // from a full run on first load.
        setParams((p) => (p.claim ? p : { ...p, claim: ex[0] ?? "" }));
      })
      .catch(() => setExamples([]));
  }, []);

  const patch = (p: Partial<AuditParams>) => setParams((prev) => ({ ...prev, ...p }));

  // `overrides` lets the resolution-path buttons re-audit with a changed setting
  // (e.g. source -> pubmed) in one click; the override is also written back to
  // the sidebar so the UI reflects what was run.
  async function audit(overrides: Partial<AuditParams> = {}) {
    const merged = { ...params, ...overrides };
    if (Object.keys(overrides).length) setParams(merged);
    if (!merged.claim.trim()) {
      setError("Enter a claim to audit.");
      return;
    }
    setLoading(true);
    setError(null);
    setStatus(merged.source === "pubmed" ? "Searching PubMed…" : "Auditing the claim…");
    try {
      const res = await runAudit(merged);
      setResult(res);
    } catch (e) {
      // Keep the previous report on screen rather than blanking it on failure.
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
      setStatus("");
    }
  }

  return (
    <div className="app">
      <div className="mobile-topbar">
        <button
          className="hamburger"
          aria-label="Open settings menu"
          aria-expanded={sidebarOpen}
          onClick={() => setSidebarOpen(true)}
        >
          ☰
        </button>
        <span className="brand">
          <span className="logo">🔬</span>BioClaim Auditor
        </span>
      </div>

      {sidebarOpen && (
        <div className="backdrop" onClick={() => setSidebarOpen(false)} />
      )}

      <Sidebar
        params={params}
        onChange={patch}
        examples={examples}
        onPickExample={(claim) => {
          patch({ claim });
          setSidebarOpen(false);
        }}
        disabled={loading}
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="main">
        <h1 className="page-title">Audit a biological claim</h1>
        <p className="page-intro">
          <strong>Not a search engine.</strong> Give it one biological claim and
          it audits it: supporting vs. conflicting evidence, citation
          faithfulness, overclaims, contradictions, and what would change the
          verdict.
        </p>

        <div className="claim-card">
          <textarea
            className="claim-input"
            placeholder="e.g. BRAF V600E melanoma is associated with response to targeted inhibitor treatment."
            value={params.claim}
            onChange={(e) => patch({ claim: e.target.value })}
            onKeyDown={(e) => {
              if ((e.metaKey || e.ctrlKey) && e.key === "Enter") audit();
            }}
          />
          <div className="claim-actions">
            <button className="btn-primary" onClick={() => audit()} disabled={loading}>
              {loading && <span className="spinner" />}
              {loading ? "Auditing…" : "Audit claim"}
            </button>
            {status && <span className="status-line">{status}</span>}
            {!loading && !status && (
              <span className="status-line">⌘/Ctrl + Enter to run</span>
            )}
          </div>
        </div>

        {error && <div className="error-banner">{error}</div>}
        {result?.reviewer_warning && (
          <div className="warn-banner">{result.reviewer_warning}</div>
        )}

        {result ? (
          <Results result={result} onReaudit={audit} loading={loading} />
        ) : (
          !error && (
            <div className="empty-state">
              <div className="big">🧫</div>
              Enter a claim and run an audit to see the verdict, evidence map,
              and flags.
            </div>
          )
        )}
      </main>
    </div>
  );
}
