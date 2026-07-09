import json
import logging
from typing import List

from botocore.exceptions import ClientError, BotoCoreError

from app.services.bedrock_service import bedrock
from app.services.database import db

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are DIVEL AI, a Digital Evidence Investigation Assistant.\n\n"
    "Answer ONLY from the supplied evidence.\n"
    "Never invent information.\n"
    "If the answer is unavailable, reply:\n"
    '"I cannot find this information in the uploaded evidence."\n'
)

MAX_EVIDENCE_CONTEXT_CHARS = 14000


def _extract_response_text(response: dict) -> str:
    if "body" not in response:
        return ""

    body = response["body"]
    if hasattr(body, "read"):
        raw_bytes = body.read()
        return raw_bytes.decode("utf-8", errors="ignore") if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)

    return str(body)


def _build_prompt(case_id: str, summaries: List[str], question: str) -> str:
    merged = "\n\n".join(summaries)
    if len(merged) > MAX_EVIDENCE_CONTEXT_CHARS:
        logger.warning(
            "Merged evidence context for case_id=%s exceeds %d chars; truncating.",
            case_id,
            MAX_EVIDENCE_CONTEXT_CHARS,
        )
        merged = merged[:MAX_EVIDENCE_CONTEXT_CHARS]

    return (
        f"Case ID: {case_id}\n\n"
        f"Case Evidence:\n{merged}\n\n"
        f"Officer Question:\n{question}\n\n"
        "Answer:" 
    )


def _get_case_summaries(case_id: str) -> List[str]:
    evidence_list = db.list_case_evidence(case_id)
    summaries = []
    for evidence in evidence_list:
        filename = evidence.get("filename") or evidence.get("evidence_id") or "unknown"
        file_type = evidence.get("content_type") or evidence.get("file_type") or "unknown"
        summary = (evidence.get("ai_summary") or evidence.get("summary") or evidence.get("generated_summary") or "")

        if summary and isinstance(summary, str) and summary.strip():
            summaries.append(
                f"Evidence:\n"
                f"File Name: {filename}\n"
                f"File Type: {file_type}\n"
                f"AI Summary:\n{summary.strip()}"
            )
        else:
            processing_status = evidence.get("processing_status") or "NOT_SUPPORTED"
            summaries.append(
                f"Evidence:\n"
                f"File Name: {filename}\n"
                f"File Type: {file_type}\n"
                f"Processing Status: {processing_status}"
            )

    logger.debug("Built prompt summaries for %d evidence items for case_id=%s", len(summaries), case_id)
    return summaries


def generate_chat_answer(case_id: str, question: str) -> str:
    """Generate a concise answer from stored evidence summaries using Bedrock."""
    if not case_id or not case_id.strip():
        raise ValueError("case_id is required")
    if not question or not question.strip():
        raise ValueError("question is required")

    summaries = _get_case_summaries(case_id)
    if not summaries:
        logger.info("No stored summaries found for case_id=%s", case_id)
        return "I cannot find this information in the uploaded evidence."

    if not bedrock.client:
        logger.warning("Bedrock client not available for chat assistant.")
        return "I cannot find this information in the uploaded evidence."

    prompt = _build_prompt(case_id, summaries, question)
    # Combine system instructions with the prompt into a single user input
    full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
    logger.info("Sending chat prompt to Bedrock converse for case_id=%s", case_id)
    logger.debug("Bedrock chat full_prompt: %s", full_prompt)

    try:
        # Use Amazon Nova for answer generation per architecture requirements.
        resp = bedrock.converse(model_id="amazon.nova-lite-v1:0", input_text=full_prompt)
        raw_text = (resp or {}).get("text", "").strip()
        elapsed = (resp or {}).get("elapsed")
        usage = (resp or {}).get("usage")

        logger.debug("Bedrock raw chat response: %s", raw_text)
        if elapsed is not None:
            logger.info("Bedrock chat request completed in %.3fs", elapsed)
        if usage:
            logger.info("Bedrock chat usage info: %s", usage)

        if not raw_text:
            logger.warning("Bedrock returned an empty chat answer for case_id=%s", case_id)
            return "I cannot find this information in the uploaded evidence."

        return raw_text
    except ClientError as client_err:
        logger.exception("Bedrock ClientError generating chat answer for case_id=%s: %s", case_id, client_err)
        return "I cannot find this information in the uploaded evidence."
    except Exception as exc:
        logger.exception("Failed to generate chat answer for case_id=%s: %s", case_id, exc)
        return "I cannot find this information in the uploaded evidence."
