"""One-time backfill: index existing evidence AI summaries into the RAG vector store.

Raw extracted text isn't persisted for evidence uploaded before the RAG feature existed,
so this indexes each evidence item's stored `ai_summary` instead. Run manually:

    venv/Scripts/python tools/backfill_rag_index.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.database import db
from app.services.rag.indexer import index_evidence


def run():
    cases = db.list_cases()
    indexed = 0
    skipped = 0

    for case in cases:
        case_id = case.get("id")
        evidence_list = case.get("evidence") or db.list_case_evidence(case_id) or []

        for evidence in evidence_list:
            evidence_id = evidence.get("evidence_id") or evidence.get("id")
            filename = evidence.get("filename") or evidence.get("name") or "unknown"
            metadata = evidence.get("metadata", evidence)
            ai_summary = metadata.get("ai_summary") or evidence.get("ai_summary")

            if not evidence_id or not ai_summary:
                skipped += 1
                continue

            index_evidence(case_id=case_id, evidence_id=evidence_id, filename=filename, ai_summary=ai_summary)
            indexed += 1

    print(f"Backfill complete. Indexed {indexed} evidence item(s), skipped {skipped} (no id or no summary).")


if __name__ == "__main__":
    run()
