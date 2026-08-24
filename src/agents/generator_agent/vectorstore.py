"""ChromaDB vector store for support-ticket RAG (lazy client)."""

from __future__ import annotations

from pathlib import Path

from config.settings import CHROMA_PERSIST_DIR

COLLECTION_NAME = "support_tickets"

_client = None


def _get_client(persist_dir: str | Path | None = None):
    global _client
    path = str(persist_dir or CHROMA_PERSIST_DIR)
    Path(path).mkdir(parents=True, exist_ok=True)
    if _client is None or persist_dir is not None:
        import chromadb

        client = chromadb.PersistentClient(path=path)
        if persist_dir is None:
            _client = client
        return client
    return _client


def get_collection(name: str = COLLECTION_NAME, *, persist_dir: str | Path | None = None):
    return _get_client(persist_dir).get_or_create_collection(name=name)


def collection_count(name: str = COLLECTION_NAME, *, persist_dir: str | Path | None = None) -> int:
    return int(get_collection(name, persist_dir=persist_dir).count())


def reset_collection(name: str = COLLECTION_NAME, *, persist_dir: str | Path | None = None) -> None:
    client = _get_client(persist_dir)
    try:
        client.delete_collection(name)
    except Exception:
        pass
    client.get_or_create_collection(name=name)


def index_documents(
    texts: list[str],
    metadatas: list[dict],
    ids: list[str],
    *,
    embeddings: list[list[float]] | None = None,
    persist_dir: str | Path | None = None,
    collection_name: str = COLLECTION_NAME,
) -> int:
    """Index ticket snippets. Embeddings optional (Chroma default if omitted)."""
    if not (len(texts) == len(metadatas) == len(ids)):
        raise ValueError("texts, metadatas, and ids must have the same length")
    if not texts:
        return 0

    collection = get_collection(collection_name, persist_dir=persist_dir)
    kwargs = {
        "documents": texts,
        "metadatas": metadatas,
        "ids": ids,
    }
    if embeddings is not None:
        kwargs["embeddings"] = embeddings
    collection.upsert(**kwargs)
    return len(texts)
