"""Render docs/scan_shift.svg — the verdict-shift figure for the PubMed scan.

Visualises `outputs/example_pubmed_scan.md`: the same ten well-known claims read
two ways off live PubMed — the offline deterministic extractor vs the real Claude
extractor — as a dumbbell / shift chart. The horizontal axis is the tool's stance
toward the claim, from *endorses* (well-supported, left) to *rejects*
(contradicted, right). Each row shows where the deterministic rules land (hollow
ring) and where Claude lands (filled dot), joined by an arrow.

The story reads at a glance: on established oncology claims the two agree (no
arrow); on debunked claims the deterministic rules either miss the evidence or —
for beta-carotene and vitamin C — actively grade a *harmful/null* claim as
well-supported (far left, green), while Claude pulls it all the way to
contradicted (far right, red). Those two rows are flagged.

Self-contained SVG (no external assets), so it embeds in the README and renders
in a browser for the demo video.  Data is the committed snapshot, so this is
deterministic and offline — re-run scripts/pubmed_scan.py to refresh the numbers.

    python scripts/render_scan_shift.py
"""

from __future__ import annotations

from pathlib import Path

# Verdict columns, ordered endorses -> rejects. 'contested' keeps its slot for
# even spacing even though this snapshot has none, so the axis stays honest.
VERDICTS = ["well-supported", "contested", "mixed", "insufficient", "contradicted"]
VERDICT_IDX = {v: i for i, v in enumerate(VERDICTS)}

VERDICT_COLOR = {
    "well-supported": "#0ca30c",  # status: good
    "contested": "#ec835a",       # status: serious
    "mixed": "#fab219",           # status: warning
    "insufficient": "#898781",    # muted
    "contradicted": "#d03b3b",    # status: critical
}

# (short label, deterministic verdict, claude verdict) — from example_pubmed_scan.md
ROWS = [
    ("BRAF V600E melanoma → targeted inhibitors", "well-supported", "well-supported"),
    ("EGFR mutations → EGFR TKIs (NSCLC)", "well-supported", "well-supported"),
    ("Trastuzumab → survival in HER2+ breast cancer", "well-supported", "well-supported"),
    ("Aspirin → lower colorectal-cancer risk", "insufficient", "mixed"),
    ("Vitamin D → lower cancer risk", "insufficient", "contradicted"),
    ("Antioxidant supplements → lower mortality", "insufficient", "contradicted"),
    ("Beta-carotene → prevents lung cancer", "well-supported", "contradicted"),
    ("Vitamin C → prevents the common cold", "well-supported", "contradicted"),
    ("Ivermectin → lower COVID-19 mortality", "insufficient", "contradicted"),
    ("Hydroxychloroquine → lower COVID-19 mortality", "insufficient", "contradicted"),
    ("MMR vaccine → causes autism", "insufficient", "contradicted"),
    ("HRT → prevents coronary heart disease", "insufficient", "contradicted"),
    ("Arthroscopic knee surgery → beats placebo", "well-supported", "contradicted"),
    ("Statins → fewer cardiovascular events", "insufficient", "insufficient"),
    ("Semaglutide → lower body weight (obesity)", "insufficient", "well-supported"),
    ("Aducanumab → slows Alzheimer's decline", "insufficient", "well-supported"),
]

# A row is "dangerous" when the deterministic rules actively endorse
# (well-supported) a claim the literature has debunked (Claude: contradicted).
def is_dangerous(det: str, claude: str) -> bool:
    return det == "well-supported" and claude == "contradicted"


INK = "#0b0b0b"
MUTED = "#6b6b66"
SURFACE = "#fcfcfb"
PANEL = "#f4f2ec"
DANGER_BAND = "#fdecec"
DANGER_EDGE = "#d03b3b"
TRACK = "#eceae3"

FONT = "ui-sans-serif,system-ui,-apple-system,Segoe UI,Roboto,sans-serif"


def esc(text: str) -> str:
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def main() -> None:
    root = Path(__file__).resolve().parents[1]

    # Layout ---------------------------------------------------------------
    W = 900
    left = 30
    label_w = 300               # claim label column
    plot_x0 = left + label_w + 20
    plot_x1 = W - 72             # right margin leaves room for the 'contradicted' label
    n = len(VERDICTS)
    col_x = [plot_x0 + (plot_x1 - plot_x0) * i / (n - 1) for i in range(n)]

    header_h = 58
    axis_y = header_h + 92      # y of the verdict column headers
    row_h = 40
    rows_top = axis_y + 26
    H = rows_top + row_h * len(ROWS) + 120

    p: list[str] = []
    p.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" font-family="{FONT}">'
    )
    p.append(f'<rect x="6" y="6" width="{W-12}" height="{H-12}" rx="14" fill="{SURFACE}" '
             f'stroke="#dddad0" stroke-width="1.5"/>')

    # Header ---------------------------------------------------------------
    p.append(f'<rect x="6" y="6" width="{W-12}" height="{header_h}" rx="14" fill="{PANEL}"/>')
    p.append(f'<rect x="6" y="{header_h-8}" width="{W-12}" height="16" fill="{PANEL}"/>')
    p.append(f'<circle cx="30" cy="34" r="8" fill="none" stroke="{INK}" stroke-width="2.5"/>')
    p.append(f'<line x1="36" y1="40" x2="42" y2="46" stroke="{INK}" stroke-width="2.5" stroke-linecap="round"/>')
    p.append(f'<text x="52" y="30" font-size="18" font-weight="700" fill="{INK}">'
             'Deterministic rules vs Claude, over 16 known claims on live PubMed</text>')
    p.append(f'<text x="52" y="48" font-size="12.5" fill="{MUTED}">'
             'Where each extractor lands the verdict — agreement, honest gaps, and three dangerous misses</text>')

    # Axis header: verdict columns ----------------------------------------
    present = {det for _, det, _ in ROWS} | {cl for _, _, cl in ROWS}
    p.append(f'<text x="{left}" y="{axis_y-24}" font-size="11" letter-spacing="1.2" fill="{MUTED}">'
             'STANCE TOWARD THE CLAIM</text>')
    # endorses -> rejects direction hint
    p.append(f'<text x="{plot_x0}" y="{axis_y-24}" font-size="11" fill="{MUTED}">endorses</text>')
    p.append(f'<text x="{plot_x1}" y="{axis_y-24}" font-size="11" fill="{MUTED}" text-anchor="end">rejects</text>')
    p.append(f'<line x1="{plot_x0}" y1="{axis_y-18}" x2="{plot_x1}" y2="{axis_y-18}" '
             f'stroke="#e6e4dd" stroke-width="1"/>')
    for i, v in enumerate(VERDICTS):
        col = VERDICT_COLOR[v]
        faded = v not in present
        op = "0.35" if faded else "1"
        p.append(f'<circle cx="{col_x[i]:.1f}" cy="{axis_y}" r="4.5" fill="{col}" fill-opacity="{op}"/>')
        # short header label, wrapped onto two lines by splitting on '-'
        short = v.replace("well-supported", "well-⁠supported")
        p.append(f'<text x="{col_x[i]:.1f}" y="{axis_y+20}" font-size="11" text-anchor="middle" '
                 f'fill="{INK if not faded else MUTED}" fill-opacity="{op}">{esc(v)}</text>')

    # Faint vertical guides at each column
    for i in range(n):
        p.append(f'<line x1="{col_x[i]:.1f}" y1="{rows_top-6}" x2="{col_x[i]:.1f}" '
                 f'y2="{rows_top + row_h*len(ROWS) - row_h + 6:.1f}" stroke="#efeee8" stroke-width="1"/>')

    # Rows -----------------------------------------------------------------
    for r, (label, det, claude) in enumerate(ROWS):
        cy = rows_top + row_h * r + row_h / 2
        danger = is_dangerous(det, claude)
        if danger:
            p.append(f'<rect x="16" y="{cy-row_h/2+3:.1f}" width="{W-32}" height="{row_h-6}" rx="8" '
                     f'fill="{DANGER_BAND}"/>')
            p.append(f'<rect x="16" y="{cy-row_h/2+3:.1f}" width="3.5" height="{row_h-6}" rx="1.5" '
                     f'fill="{DANGER_EDGE}"/>')

        p.append(f'<text x="{left}" y="{cy+4:.1f}" font-size="12.5" fill="{INK}">{esc(label)}</text>')

        dx = col_x[VERDICT_IDX[det]]
        cx = col_x[VERDICT_IDX[claude]]
        det_col = VERDICT_COLOR[det]
        cl_col = VERDICT_COLOR[claude]

        if det == claude:
            # Agreement: one filled dot with a ring, plus a small "agree" note.
            p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{cl_col}"/>')
            p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="none" stroke="{SURFACE}" stroke-width="2"/>')
            p.append(f'<text x="{cx+14:.1f}" y="{cy+4:.1f}" font-size="10.5" fill="{MUTED}">agree</text>')
            continue

        # Disagreement: arrow from deterministic (hollow) to Claude (filled).
        # Arrow colored by Claude's verdict (the corrected landing point).
        x0, x1 = (dx, cx)
        direction = 1 if x1 > x0 else -1
        gap = 9
        sx = x0 + direction * gap
        ex = x1 - direction * gap
        stroke_w = "3" if danger else "2"
        p.append(f'<line x1="{sx:.1f}" y1="{cy:.1f}" x2="{ex:.1f}" y2="{cy:.1f}" '
                 f'stroke="{cl_col}" stroke-width="{stroke_w}" stroke-linecap="round"/>')
        # arrowhead at Claude end
        ah = 5.5
        p.append(f'<path d="M {ex:.1f} {cy:.1f} l {-direction*ah:.1f} {-ah:.1f} '
                 f'l 0 {2*ah:.1f} z" fill="{cl_col}"/>')
        # deterministic marker: hollow ring in its own verdict color
        p.append(f'<circle cx="{dx:.1f}" cy="{cy:.1f}" r="6" fill="{SURFACE}" '
                 f'stroke="{det_col}" stroke-width="2.5"/>')
        # Claude marker: filled dot
        p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="{cl_col}"/>')
        p.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="7" fill="none" stroke="{SURFACE}" stroke-width="2"/>')

    # Danger callout -------------------------------------------------------
    band_y = rows_top + row_h * len(ROWS) + 6
    p.append(f'<rect x="16" y="{band_y}" width="{W-32}" height="1" fill="#e6e4dd"/>')
    p.append(f'<circle cx="26" cy="{band_y+22}" r="4.5" fill="{DANGER_EDGE}"/>')
    p.append(f'<text x="38" y="{band_y+26}" font-size="12.5" fill="{INK}">'
             '<tspan font-weight="700">Three dangerous misses.</tspan> '
             'The deterministic rules grade <tspan font-weight="600">beta-carotene → lung cancer</tspan>, '
             '<tspan font-weight="600">vitamin C → colds</tspan>, and</text>')
    p.append(f'<text x="38" y="{band_y+44}" font-size="12.5" fill="{INK}">'
             '<tspan font-weight="600">arthroscopic knee surgery → beats placebo</tspan> as well-supported. '
             'Claude reads the abstracts and contradicts all three.</text>')

    # Legend ---------------------------------------------------------------
    ly = band_y + 74
    p.append(f'<circle cx="30" cy="{ly}" r="6" fill="{SURFACE}" stroke="{MUTED}" stroke-width="2.5"/>')
    p.append(f'<text x="42" y="{ly+4}" font-size="12" fill="{INK}">Deterministic (offline rules)</text>')
    p.append(f'<circle cx="240" cy="{ly}" r="7" fill="{MUTED}"/>')
    p.append(f'<circle cx="240" cy="{ly}" r="7" fill="none" stroke="{SURFACE}" stroke-width="2"/>')
    p.append(f'<text x="252" y="{ly+4}" font-size="12" fill="{INK}">Claude extractor</text>')
    p.append(f'<text x="{plot_x1:.0f}" y="{ly+4}" font-size="11" fill="{MUTED}" text-anchor="end" '
             'font-style="italic">snapshot of scripts/pubmed_scan.py · live PubMed · claude-opus-4-8</text>')

    p.append("</svg>")

    out = root / "docs" / "scan_shift.svg"
    out.write_text("".join(p), encoding="utf-8")
    print(f"wrote {out} ({out.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
