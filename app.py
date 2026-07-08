"""BioClaim Auditor — Streamlit UI.

A thin front-end over the library: claim in, reviewable Claim Audit Report out.
It reuses the exact same pipeline as the CLI (`build_evidence_card` -> `audit_card`
-> `review_card` -> `render_claim_audit`), so the UI can never diverge from the
audited core. Run it containerized:

    docker compose up            # then open http://localhost:8501

or locally with the optional extra:

    pip install '.[ui]' && streamlit run app.py
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from biomedical_evidence_agent.audit import audit_card
from biomedical_evidence_agent.evidence import build_evidence_card
from biomedical_evidence_agent.report import audit_json, render_claim_audit
from biomedical_evidence_agent.retrieval import (
    ConceptAwareRetriever,
    LexicalRetriever,
    load_corpus,
)
from biomedical_evidence_agent.reviewer import (
    ReviewerUnavailable,
    anthropic_reviewer,
    mock_reviewer,
    review_card,
)
from biomedical_evidence_agent.schemas import RetrievedRecord

# Resolve the corpus relative to this file, not the installed package location, so
# it works both from the repo (data/ at the root) and in Docker (/app/data).
CORPUS_PATH = Path(__file__).resolve().parent / "data" / "sample_corpus.jsonl"

EXAMPLE_CLAIMS = [
    "BRAF V600E melanoma is associated with response to targeted inhibitor treatment.",
    "IL-17A blockade may reduce fibrosis progression in systemic sclerosis.",
    "TREM2 is associated with Alzheimer's disease progression.",
    "TP53 mutation definitively cures colorectal cancer with salbutamol.",
]

_VERDICT_COLOR = {
    "well-supported": "#1a7f37",
    "mixed": "#9a6700",
    "contested": "#bf8700",
    "insufficient": "#6e7781",
}
_SEVERITY_ST = {"high": st.error, "warn": st.warning, "info": st.success}


@st.cache_data(show_spinner=False)
def _load_records(path_str: str):
    return load_corpus(Path(path_str))


def _retrieve(claim: str, source: str, retriever_name: str, top_k: int):
    if source == "pubmed":
        from biomedical_evidence_agent.pubmed import PubMedError, search_pubmed

        try:
            records = search_pubmed(claim, top_k=top_k)
        except PubMedError as exc:
            raise RuntimeError(f"PubMed error: {exc}") from exc
        return [
            RetrievedRecord(record=r, score=1.0 - i * 0.05)
            for i, r in enumerate(records)
        ]
    records = _load_records(str(CORPUS_PATH))
    retriever = (
        LexicalRetriever(records)
        if retriever_name == "lexical"
        else ConceptAwareRetriever(records)
    )
    return retriever.search(claim, top_k=top_k)


def _build_reviewer(name: str):
    if name == "none":
        return None
    if name == "mock":
        return mock_reviewer()
    return anthropic_reviewer()


def main() -> None:
    st.set_page_config(page_title="BioClaim Auditor", page_icon="🔬", layout="wide")
    st.title("🔬 BioClaim Auditor")
    st.markdown(
        "**A claim-auditing tool for life sciences evidence.** "
        "Not a search engine — give it one biological claim and it audits it: "
        "supporting vs conflicting evidence, citation faithfulness, overclaims, "
        "contradictions, and what would change the verdict."
    )
    st.caption("Research signal only — not medical advice, no patient data, toy/sample data by default.")

    with st.sidebar:
        st.header("Settings")
        source = st.radio("Source", ["sample", "pubmed"], help="PubMed uses public metadata only.")
        retriever_name = st.selectbox("Retriever", ["concept", "lexical"], disabled=source == "pubmed")
        top_k = st.slider("Records retrieved (top-k)", 1, 10, 5)
        reviewer_name = st.selectbox(
            "Reviewer", ["mock", "none", "claude"],
            help="'claude' needs the llm extra + ANTHROPIC_API_KEY.",
        )
        st.divider()
        st.caption("Example claims")
        for i, example in enumerate(EXAMPLE_CLAIMS):
            if st.button(example, key=f"ex-{i}", use_container_width=True):
                st.session_state["claim"] = example

    claim = st.text_area(
        "Claim to audit",
        value=st.session_state.get("claim", EXAMPLE_CLAIMS[0]),
        height=80,
    )
    run = st.button("Audit claim", type="primary")
    if not run:
        return
    if not claim.strip():
        st.warning("Enter a claim to audit.")
        return

    try:
        retrieved = _retrieve(claim, source, retriever_name, top_k)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    card = build_evidence_card(query=claim, retrieved=retrieved, claim=claim, source=source)
    audit = audit_card(card)

    critique = None
    if reviewer_name != "none":
        try:
            critique = review_card(card, audit, reviewer=_build_reviewer(reviewer_name))
        except ReviewerUnavailable as exc:
            st.warning(f"Claude reviewer unavailable, continuing without a critique: {exc}")

    _render(card, audit, critique)


def _render(card, audit, critique) -> None:
    label = card.verdict.label if card.verdict else "insufficient"
    color = _VERDICT_COLOR.get(label, "#6e7781")
    strength = card.verdict.strength if card.verdict else 0.0
    st.markdown(
        f"### Audit Verdict: "
        f"<span style='color:{color};font-weight:700'>{label}</span> "
        f"<span style='color:#6e7781'>(strength {strength:+.2f})</span>",
        unsafe_allow_html=True,
    )

    v = card.verdict
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Supporting sources", v.support_sources if v else 0)
    c2.metric("Conflicting sources", v.conflict_sources if v else 0)
    c3.metric("Citation faithfulness", f"{audit.citation_faithfulness * 100:.0f}%")
    c4.metric("Records retrieved", len(card.retrieved))

    if audit.findings:
        st.subheader("Audit flags")
        for flag in audit.findings:
            _SEVERITY_ST.get(flag.severity, st.info)(
                f"**{flag.category}** — {flag.message}"
                + (f"  \n_{flag.detail}_" if flag.detail else "")
            )
    else:
        st.success("No audit flags raised.")

    if critique is not None:
        st.subheader(f"Reviewer critique ({critique.reviewer})")
        st.markdown(f"_{critique.assessment}_")
        for f in critique.findings:
            quote = f"  \n> {f.source_id}: “{f.quote}”" if f.quote else ""
            st.markdown(f"- **{f.kind}:** {f.note}{quote}")

    markdown = render_claim_audit(card, audit, critique)
    with st.expander("Full Claim Audit Report (Markdown)", expanded=True):
        st.markdown(markdown)

    payload = json.dumps(audit_json(card, audit, critique), indent=2)
    d1, d2 = st.columns(2)
    d1.download_button("Download Markdown", markdown, file_name="claim_audit.md")
    d2.download_button("Download JSON", payload, file_name="claim_audit.json")


if __name__ == "__main__":
    main()
