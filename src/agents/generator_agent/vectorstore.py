"""Indexation et persistance de la base vectorielle ChromaDB."""
import chromadb
from config.settings import CHROMA_PERSIST_DIR

_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)


def get_collection(name: str = "support_tickets"):
    return _client.get_or_create_collection(name)


def index_documents(texts: list[str], metadatas: list[dict], ids: list[str]):
    """Indexe des documents (tickets) avec leurs métadonnées dans ChromaDB."""
    collection = get_collection()
    collection.add(documents=texts, metadatas=metadatas, ids=ids)
