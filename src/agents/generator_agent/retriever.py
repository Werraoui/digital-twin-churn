"""Similarity retrieval over the ticket corpus (Chroma or lexical fallback)."""

from __future__ import annotations

import re
from pathlib import Path

from src.agents.generator_agent.corpus import build_ticket_documents
from src.agents.generator_agent.embeddings import embed_texts
from src.agents.generator_agent.vectorstore import (
    COLLECTION_NAME,
    collection_count,
    get_collection,
    index_documents,
    reset_collection,
)

_TOKEN = re.compile(r"[a-z0-9]+", re.I)


def _tokenize(text: str) -> set[str]:
    return set(_TOKEN.findall(text.lower()))


def _lexical_retrieve(query: str, documents: list[dict], top_k: int) -> list[str]:
    q = _tokenize(query)
    if not q:
        return [doc["text"] for doc in documents[:top_k]]
    scored = []
    for doc in documents:
        tokens = _tokenize(doc["text"])
        overlap = len(q & tokens) / max(len(q), 1)
        scored.append((overlap, doc["text"]))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [text for score, text in scored[:top_k] if score > 0] or [
        doc["text"] for doc in documents[:top_k]
    ]


def ensure_ticket_index(
    *,
    persist_dir: str | Path | None = None,
    force_rebuild: bool = False,
    use_embeddings: bool = True,
) -> int:
    """Index unique ticket issue texts into Chroma if the collection is empty."""
    if force_rebuild:
        reset_collection(COLLECTION_NAME, persist_dir=persist_dir)
    elif collection_count(COLLECTION_NAME, persist_dir=persist_dir) > 0:
        return collection_count(COLLECTION_NAME, persist_dir=persist_dir)

    documents = build_ticket_documents()
    texts = [doc["text"] for doc in documents]
    metadatas = [doc["metadata"] for doc in documents]
    ids = [doc["id"] for doc in documents]
    embeddings = embed_texts(texts) if use_embeddings else None
    return index_documents(
        texts,
        metadatas,
        ids,
        embeddings=embeddings,
        persist_dir=persist_dir,
    )


def retrieve_context(
    query: str,
    top_k: int = 3,
    *,
    persist_dir: str | Path | None = None,
    use_chroma: bool = True,
    documents: list[dict] | None = None,
) -> list[str]:
    """
    Return the most relevant ticket snippets for a query.

    Falls back to lexical overlap on the canned corpus when Chroma is unavailable
    or the collection is empty.
    """
    query = (query or "").strip()
    if not query:
        return []

    if use_chroma:
        try:
            ensure_ticket_index(persist_dir=persist_dir)
            collection = get_collection(COLLECTION_NAME, persist_dir=persist_dir)
            if collection.count() > 0:
                try:
                    query_embedding = embed_texts([query])[0]
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=min(top_k, collection.count()),
                    )
                except Exception:
                    results = collection.query(
                        query_texts=[query],
                        n_results=min(top_k, collection.count()),
                    )
                docs = results.get("documents") or []
                if docs and docs[0]:
                    return list(docs[0])
        except Exception:
            pass

    corpus = documents if documents is not None else build_ticket_documents()
    return _lexical_retrieve(query, corpus, top_k)
