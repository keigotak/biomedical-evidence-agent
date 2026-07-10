import ReactMarkdown from "react-markdown";
import type {
  AuditResult,
  EvidenceClaim,
  EvidenceMapEntry,
} from "../types";
import { SEVERITY, STANCE_COLOR, VERDICT_COLOR } from "../constants";

export function Results({ result }: { result: AuditResult }) {
  return (
    <div className="results">
      <VerdictBanner result={result} />
      <Metrics result={result} />
      <EvidenceMap rows={result.evidence_map} />
      <Flags result={result} />
      <EvidenceLists result={result} />
      {result.reviewer_critique && (
        <Critique critique={result.reviewer_critique} />
      )}
      <MindChangers result={result} />
      <ReportPanel result={result} />
      <Downloads result={result} />
    </div>
  );
}

function VerdictBanner({ result }: { result: AuditResult }) {
  const v = result.verdict;
  const label = v?.label ?? "insufficient";
  const color = VERDICT_COLOR[label] ?? "var(--neutral)";
  const strength = v?.strength ?? 0;
  // Map strength in [-1, 1] to a fill anchored at the centre of the track.
  const pct = Math.min(Math.abs(strength), 1) * 50;
  const left = strength >= 0 ? 50 : 50 - pct;
  return (
    <div className="verdict" style={{ ["--v-color" as string]: color }}>
      <div className="verdict-top">
        <span className="verdict-label">{label}</span>
        <span className="verdict-strength">
          strength {strength >= 0 ? "+" : ""}
          {strength.toFixed(2)}
        </span>
      </div>
      <div className="strength-track" title={`Net strength ${strength.toFixed(2)}`}>
        <div className="strength-mid" />
        <div
          className="strength-fill"
          style={{ left: `${left}%`, width: `${pct}%` }}
        />
      </div>
      {v?.rationale && <p className="verdict-rationale">{v.rationale}</p>}
    </div>
  );
}

function Metrics({ result }: { result: AuditResult }) {
  const v = result.verdict;
  const faith = result.citation_audit.faithfulness * 100;
  const records =
    result.evidence.supporting.length +
    result.evidence.conflicting.length +
    result.evidence.indirect.length;
  const cells = [
    { value: v?.support_sources ?? 0, label: "Supporting sources", color: "var(--good)" },
    { value: v?.conflict_sources ?? 0, label: "Conflicting sources", color: "var(--warn)" },
    {
      value: `${faith.toFixed(0)}%`,
      label: "Citation faithfulness",
      color: faith >= 99 ? "var(--good)" : faith >= 80 ? "var(--warn)" : "var(--bad)",
    },
    { value: records, label: "Evidence sentences", color: "var(--text)" },
  ];
  return (
    <div className="metrics">
      {cells.map((c, i) => (
        <div className="metric" key={i}>
          <div className="metric-value" style={{ ["--metric-color" as string]: c.color }}>
            {c.value}
          </div>
          <div className="metric-label">{c.label}</div>
        </div>
      ))}
    </div>
  );
}

function EvidenceMap({ rows }: { rows: EvidenceMapEntry[] }) {
  if (!rows.length) return null;
  const legend: [keyof typeof STANCE_COLOR, string][] = [
    ["supports", "supporting"],
    ["conflicts", "conflicting"],
    ["indirect", "indirect"],
    ["uncovered", "uncovered"],
  ];
  return (
    <section>
      <h3 className="section-title">Evidence map — coverage by claim entity</h3>
      <div className="card">
        {rows.map((e, i) => {
          const total = e.supports + e.conflicts + e.indirect;
          const segs: [keyof typeof STANCE_COLOR, number][] = [
            ["supports", e.supports],
            ["conflicts", e.conflicts],
            ["indirect", e.indirect],
          ];
          return (
            <div className="em-row" key={i}>
              <div className="em-name">
                {e.name}
                <span className="em-type">{e.type}</span>
              </div>
              <div className="em-bar">
                {total === 0 ? (
                  <div
                    className="em-seg"
                    style={{ width: "100%", background: STANCE_COLOR.uncovered }}
                  />
                ) : (
                  segs
                    .filter(([, n]) => n > 0)
                    .map(([stance, n], j) => (
                      <div
                        key={j}
                        className="em-seg"
                        title={`${stance}: ${n}`}
                        style={{
                          width: `${(n / total) * 100}%`,
                          background: STANCE_COLOR[stance],
                        }}
                      />
                    ))
                )}
              </div>
              <div className="em-summary">
                {total === 0 ? (
                  <span className="em-uncovered">
                    ⚠ unaddressed by any retrieved sentence
                  </span>
                ) : (
                  [
                    e.supports && `${e.supports} supporting`,
                    e.conflicts && `${e.conflicts} conflicting`,
                    e.indirect && `${e.indirect} indirect`,
                  ]
                    .filter(Boolean)
                    .join(" · ")
                )}
              </div>
            </div>
          );
        })}
        <div className="legend">
          {legend.map(([key, label]) => (
            <span key={key}>
              <i style={{ background: STANCE_COLOR[key] }} />
              {label}
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

function Flags({ result }: { result: AuditResult }) {
  return (
    <section>
      <h3 className="section-title">Audit flags</h3>
      <div className="card">
        {result.flags.length === 0 ? (
          <div className="no-flags">✓ No audit flags raised.</div>
        ) : (
          result.flags.map((f, i) => {
            const s = SEVERITY[f.severity] ?? SEVERITY.info;
            return (
              <div
                className="flag"
                key={i}
                style={{
                  ["--f-bg" as string]: s.bg,
                  ["--f-border" as string]: s.border,
                  ["--f-text" as string]: s.text,
                }}
              >
                <span className="flag-icon">{s.icon}</span>
                <div className="flag-body">
                  <span className="flag-cat">{f.category}</span> — {f.message}
                  {f.detail && <div className="flag-detail">{f.detail}</div>}
                </div>
              </div>
            );
          })
        )}
      </div>
    </section>
  );
}

function ClaimCard({ claim, color }: { claim: EvidenceClaim; color: string }) {
  return (
    <div className="claim-item" style={{ ["--stance-color" as string]: color }}>
      {claim.text}
      <div className="claim-meta">
        <span className="tag">{claim.source_id}</span>
        <span className="tag">{claim.tier}</span>
        <span className="tag">{claim.confidence}</span>
      </div>
    </div>
  );
}

function EvidenceLists({ result }: { result: AuditResult }) {
  const cols: {
    key: string;
    title: string;
    items: EvidenceClaim[];
    color: string;
    pillBg: string;
    pillText: string;
  }[] = [
    {
      key: "supporting",
      title: "Supporting",
      items: result.evidence.supporting,
      color: STANCE_COLOR.supports,
      pillBg: "var(--good-soft)",
      pillText: "var(--good)",
    },
    {
      key: "conflicting",
      title: "Conflicting",
      items: result.evidence.conflicting,
      color: STANCE_COLOR.conflicts,
      pillBg: "var(--warn-soft)",
      pillText: "var(--warn)",
    },
    {
      key: "indirect",
      title: "Indirect",
      items: result.evidence.indirect,
      color: STANCE_COLOR.indirect,
      pillBg: "var(--neutral-soft)",
      pillText: "var(--text-muted)",
    },
  ];
  return (
    <section>
      <h3 className="section-title">Evidence sentences by stance</h3>
      <div className="evidence-cols">
        {cols.map((c) => (
          <div className="evidence-col" key={c.key}>
            <h4>
              {c.title}
              <span
                className="count-pill"
                style={{
                  ["--pill-bg" as string]: c.pillBg,
                  ["--pill-text" as string]: c.pillText,
                }}
              >
                {c.items.length}
              </span>
            </h4>
            {c.items.length === 0 ? (
              <div className="empty-note">None.</div>
            ) : (
              c.items.map((claim, i) => (
                <ClaimCard key={i} claim={claim} color={c.color} />
              ))
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function Critique({
  critique,
}: {
  critique: NonNullable<AuditResult["reviewer_critique"]>;
}) {
  return (
    <section>
      <h3 className="section-title">Reviewer critique ({critique.reviewer})</h3>
      <div className="card">
        <p className="critique-assessment">{critique.assessment}</p>
        {critique.findings.map((f, i) => (
          <div className="critique-finding" key={i}>
            <span className="critique-kind">{f.kind}</span> — {f.note}
            {f.quote && (
              <div className="critique-quote">
                {f.source_id}: “{f.quote}”
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

function BulletCol({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <h4 className="section-title" style={{ marginBottom: 8 }}>
        {title}
      </h4>
      {items.length ? (
        <ul className="bullet-list">
          {items.map((it, i) => (
            <li key={i}>{it}</li>
          ))}
        </ul>
      ) : (
        <div className="empty-note">None.</div>
      )}
    </div>
  );
}

function MindChangers({ result }: { result: AuditResult }) {
  return (
    <section>
      <div className="bullet-grid">
        <BulletCol
          title="What would change my mind"
          items={result.what_would_change_my_mind}
        />
        <BulletCol title="Suggested next checks" items={result.next_checks} />
        <BulletCol title="Limitations" items={result.limitations} />
      </div>
    </section>
  );
}

function ReportPanel({ result }: { result: AuditResult }) {
  return (
    <details className="report">
      <summary>Full Claim Audit Report (Markdown)</summary>
      <div className="markdown">
        <ReactMarkdown>{result.markdown}</ReactMarkdown>
      </div>
    </details>
  );
}

function download(name: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

function Downloads({ result }: { result: AuditResult }) {
  const json = JSON.stringify(result, null, 2);
  return (
    <div className="downloads">
      <button
        className="btn-ghost"
        onClick={() => download("claim_audit.md", result.markdown, "text/markdown")}
      >
        ↓ Download Markdown
      </button>
      <button
        className="btn-ghost"
        onClick={() => download("claim_audit.json", json, "application/json")}
      >
        ↓ Download JSON
      </button>
    </div>
  );
}
