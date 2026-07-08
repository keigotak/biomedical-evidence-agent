"""Render the README hero image (docs/hero.svg) from real audit output.

Not a screenshot of the running Streamlit app (which needs a browser) — a
self-contained SVG "report card" built from the same pipeline the app renders,
so it is an accurate depiction of a real Claim Audit Report and embeds directly
in the GitHub README (no external assets, works on light and dark backgrounds).

    PYTHONPATH=src python scripts/render_hero.py
"""

from __future__ import annotations

from pathlib import Path

from biomedical_evidence_agent.audit import audit_card, claim_concept_coverage
from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.retrieval import ConceptAwareRetriever, load_corpus

CLAIM = "BRAF V600E melanoma is associated with response to targeted inhibitor treatment."

STANCE_COLOR = {"supports": "#0ca30c", "conflicts": "#fab219", "indirect": "#9a9a94"}
UNCOVERED = "#d03b3b"
VERDICT_COLOR = {
    "well-supported": "#0ca30c",
    "contested": "#bf8700",
    "mixed": "#9a6700",
    "contradicted": "#d03b3b",
    "insufficient": "#6e7781",
}
INK = "#0b0b0b"
MUTED = "#6b6b66"
SURFACE = "#fcfcfb"
PANEL = "#f4f2ec"


def esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    records = load_corpus(root / "data" / "sample_corpus.jsonl")
    retrieved = ConceptAwareRetriever(records).search(CLAIM, top_k=3)
    card = build_evidence_card(query=CLAIM, retrieved=retrieved, claim=CLAIM)
    audit = audit_card(card)
    coverage = claim_concept_coverage(card)
    verdict = card.verdict

    W, H = 860, 500
    p = []  # svg fragments
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif">'
    )
    # No drop-shadow filter: GitHub's SVG sanitizer can strip <filter> defs while
    # leaving the filter="" reference, which would make the referencing rect vanish.
    # A crisp border gives the card enough definition without it.
    p.append(f'<rect x="10" y="10" width="{W-20}" height="{H-20}" rx="14" fill="{SURFACE}" '
             f'stroke="#dddad0" stroke-width="1.5"/>')
    # Header
    p.append(f'<rect x="10" y="10" width="{W-20}" height="52" rx="14" fill="{PANEL}"/>')
    p.append(f'<rect x="10" y="46" width="{W-20}" height="16" fill="{PANEL}"/>')
    p.append(f'<circle cx="34" cy="36" r="8" fill="none" stroke="{INK}" stroke-width="2.5"/>')
    p.append(f'<line x1="40" y1="42" x2="46" y2="48" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>')
    p.append(f'<text x="56" y="43" font-size="20" font-weight="700" fill="{INK}">BioClaim Auditor</text>')
    p.append(f'<text x="{W-30}" y="42" font-size="12.5" fill="{MUTED}" text-anchor="end">'
             'a claim-auditing tool for life-sciences evidence</text>')

    y = 88
    p.append(f'<text x="30" y="{y}" font-size="11" letter-spacing="1.2" fill="{MUTED}">CLAIM</text>')
    y += 22
    p.append(f'<text x="30" y="{y}" font-size="16" font-weight="600" fill="{INK}">{esc(CLAIM)}</text>')

    # Verdict badge
    y += 30
    label = verdict.label if verdict else "insufficient"
    vc = VERDICT_COLOR.get(label, "#6e7781")
    strength = f"{verdict.strength:+.2f}" if verdict else "+0.00"
    badge_w = 330
    p.append(f'<rect x="30" y="{y}" width="{badge_w}" height="34" rx="17" fill="{vc}"/>')
    p.append(f'<text x="{30+badge_w/2}" y="{y+22}" font-size="13" font-weight="700" fill="#fff" '
             f'text-anchor="middle">AUDIT VERDICT · {label.upper()} {strength}</text>')
    p.append(f'<text x="{30+badge_w+16}" y="{y+22}" font-size="12.5" fill="{MUTED}">'
             '1 supporting · 1 conflicting clinical source</text>')

    # Evidence map
    y += 62
    p.append(f'<text x="30" y="{y}" font-size="11" letter-spacing="1.2" fill="{MUTED}">EVIDENCE MAP — coverage by claim entity</text>')
    y += 10
    label_x, bar_x, bar_w = 175, 190, 230
    for entry in coverage:
        y += 26
        p.append(f'<text x="{label_x}" y="{y+2}" font-size="13" fill="{INK}" text-anchor="end">'
                 f'{esc(entry["name"])}</text>')
        _sl = {"supports": "supporting", "conflicts": "conflicting", "indirect": "indirect"}
        counts = [("supports", entry["supports"]), ("conflicts", entry["conflicts"]), ("indirect", entry["indirect"])]
        total = sum(n for _, n in counts)
        p.append(f'<rect x="{bar_x}" y="{y-9}" width="{bar_w}" height="13" rx="3" fill="#eceae3"/>')
        if total == 0:
            p.append(f'<rect x="{bar_x}" y="{y-9}" width="{bar_w}" height="13" rx="3" fill="{UNCOVERED}"/>')
            p.append(f'<text x="{bar_x+bar_w+12}" y="{y+2}" font-size="12" fill="{UNCOVERED}">no evidence addresses this entity</text>')
        else:
            cx = bar_x
            for stance, n in counts:
                if not n:
                    continue
                seg = (n / total) * bar_w
                p.append(f'<rect x="{cx:.1f}" y="{y-9}" width="{max(seg-2,4):.1f}" height="13" rx="3" fill="{STANCE_COLOR[stance]}"/>')
                cx += seg
            summ = " · ".join(f"{n} {_sl[s]}" for s, n in counts if n)
            p.append(f'<text x="{bar_x+bar_w+12}" y="{y+2}" font-size="12" fill="{MUTED}">{esc(summ)}</text>')

    # Audit flags + citation
    y += 40
    p.append(f'<text x="30" y="{y}" font-size="11" letter-spacing="1.2" fill="{MUTED}">AUDIT</text>')
    y += 22
    chips = [("#0ca30c", f"citations {audit.citations_verbatim}/{audit.citations_checked} verbatim")]
    for f in audit.findings:
        col = {"high": "#d03b3b", "warn": "#bf8700", "info": "#0ca30c"}.get(f.severity, "#6e7781")
        chips.append((col, f.category))
    cx = 30
    for col, txt in chips:
        w = 22 + len(txt) * 7.2
        p.append(f'<rect x="{cx:.0f}" y="{y-15}" width="{w:.0f}" height="22" rx="11" fill="{col}" fill-opacity="0.12" stroke="{col}" stroke-opacity="0.5"/>')
        p.append(f'<circle cx="{cx+13:.0f}" cy="{y-4}" r="3.5" fill="{col}"/>')
        p.append(f'<text x="{cx+22:.0f}" y="{y}" font-size="12.5" fill="{INK}">{esc(txt)}</text>')
        cx += w + 10

    # Footer strip: what would change my mind
    y += 34
    p.append(f'<rect x="20" y="{y-16}" width="{W-40}" height="1" fill="#e6e4dd"/>')
    y += 8
    p.append(f'<text x="30" y="{y}" font-size="12" fill="{MUTED}">'
             '<tspan font-weight="700" fill="' + INK + '">What would change my mind?</tspan> '
             'An independent study on BRAF, melanoma and targeted therapy that breaks the tie.</text>')
    y += 20
    p.append(f'<text x="30" y="{y}" font-size="11" fill="{MUTED}" font-style="italic">'
             'Research signal only — not medical advice · toy/sample data by default</text>')

    p.append("</svg>")
    out = root / "docs" / "hero.svg"
    out.write_text("".join(p), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
