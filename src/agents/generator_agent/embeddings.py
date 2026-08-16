"""Génération des embeddings pour le corpus RAG (Support Ticket Dataset)."""
from sentence_transformers import SentenceTransformer

_model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_texts(texts: list[str]) -> list:
    """Transforme une liste de textes en vecteurs numériques."""
    return _model.encode(texts).tolist()
