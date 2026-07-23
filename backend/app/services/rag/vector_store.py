import logging
import os
from typing import Any, Dict, List

from app.services.rag.embedding_service import embedding_function

logger = logging.getLogger(__name__)

PERSIST_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "vector_db")
COLLECTION_NAME = "evidence_chunks"

_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        import chromadb
        os.makedirs(PERSIST_DIR, exist_ok=True)
        _client = chromadb.PersistentClient(path=PERSIST_DIR)
        _collection = _client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=embedding_function,
        )
    return _collection


def upsert_chunks(case_id: str, evidence_id: str, filename: str, chunks: List[str]) -> None:
    """Embed and store text chunks for a piece of evidence, replacing any previously stored chunks for it."""
    if not chunks:
        return

    collection = _get_collection()

    try:
        collection.delete(where={"evidence_id": evidence_id})
    except Exception:
        pass

    ids = [f"{evidence_id}::{i}" for i in range(len(chunks))]
    metadatas = [
        {"case_id": case_id, "evidence_id": evidence_id, "filename": filename or "", "chunk_index": i}
        for i in range(len(chunks))
    ]
    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
    logger.info("Indexed %d chunk(s) for evidence_id=%s case_id=%s", len(chunks), evidence_id, case_id)


def get_case_chunks(case_id: str) -> List[Dict[str, Any]]:
    """Fetch every indexed chunk belonging to a case, grouped implicitly by evidence_id via metadata."""
    collection = _get_collection()
    result = collection.get(where={"case_id": case_id})

    documents = result.get("documents") or []
    metadatas = result.get("metadatas") or []

    chunks = []
    for doc, meta in zip(documents, metadatas):
        chunks.append({"text": doc, **(meta or {})})
    return chunks
