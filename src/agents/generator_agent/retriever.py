"""Recherche par similarité (retrieval) dans la base vectorielle."""
from src.agents.generator_agent.vectorstore import get_collection


def retrieve_context(query: str, top_k: int = 3) -> list[str]:
    """Retourne les documents les plus pertinents pour une requête donnée."""
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=top_k)
    return results["documents"][0] if results["documents"] else []
