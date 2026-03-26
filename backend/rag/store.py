"""ChromaDB vector store setup for the RAG knowledge base.

Falls back gracefully if ChromaDB is not available (e.g., Python 3.14 incompatibility).
"""
from pathlib import Path

CHROMA_DIR = Path("chroma_data")
_CHROMADB_AVAILABLE = False

try:
    import chromadb
    _CHROMADB_AVAILABLE = True
except Exception:
    chromadb = None


def is_available() -> bool:
    """Check if ChromaDB is usable."""
    return _CHROMADB_AVAILABLE


def get_client():
    """Get or create a persistent ChromaDB client."""
    if not _CHROMADB_AVAILABLE:
        return None
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def get_collection(name: str = "experiences"):
    """Get or create a ChromaDB collection."""
    client = get_client()
    if client is None:
        return None
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )


def reset_collection(name: str = "experiences"):
    """Delete and recreate a collection."""
    client = get_client()
    if client is None:
        return None
    try:
        client.delete_collection(name)
    except (ValueError, Exception):
        pass
    return client.get_or_create_collection(
        name=name,
        metadata={"hnsw:space": "cosine"},
    )
