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


def build_structured_summary(case: Dict[str, Any], evidence_list: List[Dict[str, Any]] = None, evidence_summaries: List[str] = None) -> str:
    case_num = case.get('caseNumber', 'N/A')
    district = case.get('district', 'N/A')
    unit = case.get('unit', 'N/A')
    status = case.get('status', 'Under Investigation')
    date_offence = case.get('dateOfOffence', 'N/A')
    date_report = case.get('dateOfReport', 'N/A')
    scene = case.get('sceneOfCrime', 'N/A')
    sections = ", ".join(case.get('lawSections', []) or []) or "N/A"
    
    narrative_parts = [
        f"Case {case_num} is registered under {unit} ({district}) with status '{status}'. The offence occurred on {date_offence} at {scene} (reported on {date_report}). Law sections applicable: {sections}."
    ]

    accused = case.get('accused') or []
    if accused:
        acc_details = []
        for a in accused:
            name = a.get('name', 'Unknown')
            acc_status = a.get('status', 'Under Investigation')
            details = f"{name} (Status: {acc_status}"
            if a.get('age'):
                details += f", Age: {a.get('age')}"
            if a.get('gender'):
                details += f", Gender: {a.get('gender')}"
            details += ")"
            acc_details.append(details)
        narrative_parts.append(f"Accused Individuals: {'; '.join(acc_details)}.")

    if case.get('contrabandType'):
        narrative_parts.append(f"Contraband Involved: {case.get('contrabandType')} (Quantity: {case.get('contrabandQuantity', 'Unspecified')}).")

    if case.get('vehicleDetails'):
        narrative_parts.append(f"Vehicle Details: {case.get('vehicleDetails')}.")

    if evidence_list:
        ev_items = [f"{e.get('name') or e.get('filename') or e.get('id')} ({e.get('type') or e.get('content_type', 'Evidence')})" for e in evidence_list]
        narrative_parts.append(f"Evidence Items ({len(evidence_list)}): {', '.join(ev_items)}.")
    elif evidence_summaries:
        narrative_parts.append(f"Evidence Summaries: {'; '.join(evidence_summaries)}.")
    else:
        narrative_parts.append("No physical or digital evidence has been attached to this case yet.")

    return "\n\n".join(narrative_parts)


def summarize_case(case_id: str) -> str:
    """Generate a case-level narrative summary from case metadata and evidence summaries, and persist it."""
    case = db.get_case(case_id)
    if not case:
        raise ValueError(f"Case '{case_id}' not found")

    evidence_list = case.get("evidence") or db.list_case_evidence(case_id) or []
    evidence_summaries = _evidence_summaries(case_id, evidence_list)

    summary_text = ""
    if bedrock.client:
        prompt = prompt_builder.build_case_summary_prompt(case, evidence_summaries)
        try:
            resp = bedrock.converse(model_id=settings.BEDROCK_SUMMARY_MODEL_ID, input_text=prompt)
            summary_text = (resp or {}).get("text", "").strip()
        except Exception as exc:
            logger.exception("Failed to generate case summary for case_id=%s: %s", case_id, exc)

    # Filter out empty, error, or content filter blocked messages from LLM
    is_invalid = (
        not summary_text
        or "content filter" in summary_text.lower()
        or "blocked by" in summary_text.lower()
        or summary_text == FALLBACK_MESSAGE
    )

    if is_invalid:
        logger.info("Using structured fallback summary for case_id=%s (LLM returned blocked/empty summary)", case_id)
        summary_text = build_structured_summary(case, evidence_list, evidence_summaries)

    updated_case = dict(case)
    updated_case["aiSummary"] = summary_text
    updated_case["updatedAt"] = str(datetime.now())
    db.create_case(updated_case)

    return summary_text

