from __future__ import annotations

import math

from .schemas import CorpusRecord, RetrievedRecord

# Optional dense-retrieval backend. It is intentionally isolated so the default
# workflow keeps running with zero dependencies and no network access. The heavy
# model is imported lazily; when it is absent the caller gets a clear, actionable
# error instead of an ImportError deep in the stack.
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingUnavailable(RuntimeError):
    """Raised when the optional embedding backend cannot be initialized."""


def _load_model(model_name: str):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise EmbeddingUnavailable(
            "Embedding retrieval requires the optional 'semantic' extra. "
            "Install it with: pip install '.[semantic]'"
        ) from exc
    try:
        # Pin CPU: retrieval embeddings are small and this avoids depending on a
        # working local CUDA toolchain, which keeps the optional path portable.
        return SentenceTransformer(model_name, device="cpu")
    except OSError as exc:  # pragma: no cover - depends on model cache/network
        raise EmbeddingUnavailable(
            f"Could not load embedding model '{model_name}': {exc}"
        ) from exc


class EmbeddingRetriever:
    """Dense retriever that ranks records by cosine similarity of embeddings.

    This complements the lexical and concept-aware retrievers rather than
    replacing them: it catches paraphrase-level similarity that neither exact
    tokens nor ontology concepts express. It is opt-in because it pulls a model.
    """

    def __init__(self, records: list[CorpusRecord], *, model_name: str = DEFAULT_MODEL):
        self.records = records
        self._model = _load_model(model_name)
        self._doc_vectors = self._model.encode(
            [self._record_text(record) for record in records]
        )

    def search(self, query: str, top_k: int = 3) -> list[RetrievedRecord]:
        query_vector = self._model.encode([query])[0]
        ranked: list[RetrievedRecord] = []
        for record, vector in zip(self.records, self._doc_vectors):
            score = self._cosine(query_vector, vector)
            if score > 0:
                ranked.append(RetrievedRecord(record=record, score=round(float(score), 4)))
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    @staticmethod
    def _record_text(record: CorpusRecord) -> str:
        entity_text = " ".join(
            value for values in record.entities.values() for value in values
        )
        return f"{record.title} {entity_text} {record.abstract}"

    @staticmethod
    def _cosine(left, right) -> float:
        numerator = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(a * a for a in left))
        right_norm = math.sqrt(sum(b * b for b in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return numerator / (left_norm * right_norm)
