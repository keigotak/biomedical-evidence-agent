"""FastAPI backend for the React front-end.

A thin HTTP layer over the exact same pipeline the CLI and the Streamlit app use
(`build_evidence_card` -> `audit_card` -> `review_card` -> `audit_json`), so the
API can never diverge from the audited core. The React app in ``web/`` is the
only consumer; in production its built assets are served from this same app.

Run it:

    uv run --extra api --extra ui uvicorn biomedical_evidence_agent.api:app --reload

or via the factory (``create_app()``). ``POST /api/audit`` takes a claim plus the
same settings the sidebar exposes and returns the machine-readable audit report
(the ``audit_json`` payload) with the rendered Markdown alongside it.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field

from .audit import audit_card
from .evidence import build_evidence_card
from .report import audit_json, render_claim_audit
from .retrieval import (
    ConceptAwareRetriever,
    LexicalRetriever,
    load_corpus,
)
from .reviewer import (
    ReviewerUnavailable,
    anthropic_reviewer,
    mock_reviewer,
    review_card,
)
from .schemas import RetrievedRecord

# Resolve the corpus relative to the repo root (two levels up from this module:
# src/biomedical_evidence_agent/api.py -> repo root), matching how the Streamlit
# app resolves it, so the same sample data works from the repo and in Docker.
_REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_PATH = _REPO_ROOT / "data" / "sample_corpus.jsonl"
WEB_DIST = _REPO_ROOT / "web" / "dist"

EXAMPLE_CLAIMS = [
    "BRAF V600E melanoma is associated with response to targeted inhibitor treatment.",
    "IL-17A blockade may reduce fibrosis progression in systemic sclerosis.",
    "TREM2 is associated with Alzheimer's disease progression.",
    "TP53 mutation definitively cures colorectal cancer with salbutamol.",
]


class AuditRequest(BaseModel):
    claim: str = Field(..., min_length=1, description="The biological claim to audit.")
    source: str = Field("sample", description="'sample' (bundled corpus) or 'pubmed'.")
    retriever: str = Field("concept", description="'concept' or 'lexical' (sample source only).")
    top_k: int = Field(5, ge=1, le=10, description="Number of records to retrieve.")
    reviewer: str = Field("mock", description="'mock', 'none', or 'claude'.")


_corpus_cache: dict[str, list] = {}


def _load_records(path: Path):
    key = str(path)
    if key not in _corpus_cache:
        _corpus_cache[key] = load_corpus(path)
    return _corpus_cache[key]


def _retrieve(claim: str, source: str, retriever_name: str, top_k: int):
    if source == "pubmed":
        from .pubmed import PubMedError, search_pubmed

        try:
            records = search_pubmed(claim, top_k=top_k)
        except PubMedError as exc:
            raise RuntimeError(f"PubMed error: {exc}") from exc
        return [
            RetrievedRecord(record=r, score=1.0 - i * 0.05)
            for i, r in enumerate(records)
        ]
    records = _load_records(CORPUS_PATH)
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


def run_audit(req: AuditRequest) -> dict:
    """Run the full pipeline for one request and return the API payload.

    Kept import-light and framework-free so it stays unit-testable: the FastAPI
    route is a one-line wrapper around this.
    """

    retrieved = _retrieve(req.claim, req.source, req.retriever, req.top_k)
    card = build_evidence_card(
        query=req.claim, retrieved=retrieved, claim=req.claim, source=req.source
    )
    audit = audit_card(card)

    critique = None
    reviewer_warning = None
    if req.reviewer != "none":
        try:
            critique = review_card(card, audit, reviewer=_build_reviewer(req.reviewer))
        except ReviewerUnavailable as exc:
            reviewer_warning = (
                f"Claude reviewer unavailable, continuing without a critique: {exc}"
            )

    payload = audit_json(card, audit, critique)
    payload["markdown"] = render_claim_audit(card, audit, critique)
    payload["records_retrieved"] = len(card.retrieved)
    payload["reviewer_warning"] = reviewer_warning
    payload["settings"] = {
        "source": req.source,
        "retriever": req.retriever,
        "top_k": req.top_k,
        "reviewer": req.reviewer,
    }
    return payload


def create_app():
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.staticfiles import StaticFiles

    app = FastAPI(
        title="BioClaim Auditor API",
        version="0.1.0",
        description="HTTP surface over the claim-audit pipeline.",
    )

    # The Vite dev server (localhost:5173) calls this API cross-origin. In prod
    # the built assets are served from this same origin, so CORS is a no-op there.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/examples")
    def examples() -> dict:
        return {"examples": EXAMPLE_CLAIMS}

    @app.get("/api/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/api/audit")
    def audit(req: AuditRequest) -> dict:
        try:
            return run_audit(req)
        except RuntimeError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    # Serve the built React app if it exists (production). During development the
    # frontend runs on the Vite dev server and this mount is simply absent.
    if WEB_DIST.is_dir():
        app.mount("/", StaticFiles(directory=str(WEB_DIST), html=True), name="web")

    return app


app = create_app()
