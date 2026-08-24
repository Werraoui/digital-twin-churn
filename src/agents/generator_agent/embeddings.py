"""Lazy sentence-transformer embeddings for the RAG corpus."""

from __future__ import annotations

_model = None
DEFAULT_MODEL_NAME = "all-MiniLM-L6-v2"


def _get_model(model_name: str = DEFAULT_MODEL_NAME):
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(model_name)
    return _model


def embed_texts(texts: list[str], *, model_name: str = DEFAULT_MODEL_NAME) -> list[list[float]]:
    """Transform a list of texts into dense vectors."""
    if not texts:
        return []
    vectors = _get_model(model_name).encode(list(texts), show_progress_bar=False)
    return [list(map(float, row)) for row in vectors]
