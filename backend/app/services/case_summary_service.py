import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from app.core.config import settings
from app.services.ai_summary import generate_summary
from app.services.bedrock_service import bedrock
from app.services.database import db
from app.services.prompt_builder import prompt_builder
from app.services.rag.vector_store import get_case_chunks

logger = logging.getLogger(__name__)

FALLBACK_MESSAGE = "Unable to generate a case summary at this time."


def _evidence_summaries(case_id: str, evidence_list: List[Dict[str, Any]]) -> List[str]:
    chunks_by_evidence: Dict[str, List[str]] = defaultdict(list)
    for chunk in get_case_chunks(case_id):
        evidence_id = chunk.get("evidence_id")
        if evidence_id:
            chunks_by_evidence[evidence_id].append(chunk.get("text", ""))

    summaries: List[str] = []
    for evidence in evidence_list:
        filename = evidence.get("filename") or evidence.get("name") or "unknown file"
        existing_summary = (
            evidence.get("ai_summary") or evidence.get("summary") or evidence.get("generated_summary")
        )

        if existing_summary and isinstance(existing_summary, str) and existing_summary.strip():
            summaries.append(f"{filename}: {existing_summary.strip()}")
            continue

        evidence_id = evidence.get("evidence_id") or evidence.get("id")
        chunks = chunks_by_evidence.get(evidence_id) or []
        if chunks:
            try:
                summary_text = generate_summary("\n".join(chunks))
                if summary_text:
                    summaries.append(f"{filename}: {summary_text}")
            except Exception as exc:
                logger.warning("Failed to summarize indexed chunks for evidence %s: %s", evidence_id, exc)

    return summaries


def summarize_case(case_id: str) -> str:
    """Generate a case-level narrative summary from case metadata and evidence summaries, and persist it."""
    case = db.get_case(case_id)
    if not case:
        raise ValueError(f"Case '{case_id}' not found")

    evidence_list = case.get("evidence") or db.list_case_evidence(case_id) or []
    evidence_summaries = _evidence_summaries(case_id, evidence_list)

    prompt = prompt_builder.build_case_summary_prompt(case, evidence_summaries)

    if not bedrock.client:
        logger.warning("Bedrock client not available; cannot generate case summary for case_id=%s", case_id)
        return FALLBACK_MESSAGE

    try:
        resp = bedrock.converse(model_id=settings.BEDROCK_SUMMARY_MODEL_ID, input_text=prompt)
        summary_text = (resp or {}).get("text", "").strip()
    except Exception as exc:
        logger.exception("Failed to generate case summary for case_id=%s: %s", case_id, exc)
        return FALLBACK_MESSAGE

    if not summary_text:
        return FALLBACK_MESSAGE

    updated_case = dict(case)
    updated_case["aiSummary"] = summary_text
    updated_case["updatedAt"] = str(datetime.now())
    db.create_case(updated_case)

    return summary_text
