import type { AuditParams, AuditResult } from "./types";

// Same-origin relative URLs: the Vite dev server proxies /api to FastAPI, and in
// production FastAPI serves this bundle, so no base URL is ever needed.

export async function fetchExamples(): Promise<string[]> {
  const res = await fetch("/api/examples");
  if (!res.ok) throw new Error(`Failed to load examples (${res.status})`);
  const data = (await res.json()) as { examples: string[] };
  return data.examples;
}

export async function runAudit(params: AuditParams): Promise<AuditResult> {
  const res = await fetch("/api/audit", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    let detail = `Audit failed (${res.status})`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* non-JSON error body; keep the status-based message */
    }
    throw new Error(detail);
  }
  return (await res.json()) as AuditResult;
}
