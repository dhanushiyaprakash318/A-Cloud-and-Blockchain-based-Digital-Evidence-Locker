import logging
from typing import Optional

from app.services.rag.chunker import chunk_text
from app.services.rag.vector_store import upsert_chunks

logger = logging.getLogger(__name__)


def index_evidence(
    case_id: str,
    evidence_id: str,
    filename: str,
    text_extracted: Optional[str] = None,
    ai_summary: Optional[str] = None,
) -> None:
    """Chunk and index whichever evidence text is available (prefers raw extracted text over the AI summary)."""
    source_text = (text_extracted or "").strip() or (ai_summary or "").strip()
    if not source_text:
        logger.info("No text available to index for evidence_id=%s (case_id=%s)", evidence_id, case_id)
        return

    try:
        chunks = chunk_text(source_text)
        upsert_chunks(case_id=case_id, evidence_id=evidence_id, filename=filename, chunks=chunks)
    except Exception as exc:
        logger.exception("Failed to index evidence_id=%s for case_id=%s: %s", evidence_id, case_id, exc)
