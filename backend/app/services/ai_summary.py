import json
import logging
from typing import Dict, Any

from botocore.exceptions import ClientError
from app.services.bedrock_service import bedrock

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are DIVEL AI, a Digital Evidence Investigation Assistant.\n\n"
    "Rules:\n"
    "- Answer only from the supplied evidence.\n"
    "- Never hallucinate.\n"
    "- Never invent facts.\n"
    "- Preserve names, dates, locations and evidence identifiers.\n"
    "- If information is missing, respond:\n"
    '"I cannot find this information in the uploaded evidence."\n'
)

MAX_SUMMARY_INPUT_CHARS = 15000


def _build_prompt_text(extracted_text: str) -> str:
    # Create a single prompt string that includes the system instructions
    # followed by the extracted text. The Converse API will be called with
    # this string as a single user input to avoid unsupported roles.
    return (
        SYSTEM_PROMPT
        + "\n\nExtracted Evidence Text:\n"
        + extracted_text
        + "\n\nPlease provide a concise, professional summary of the evidence above."
    )


def _decode_response_body(response: Any) -> str:
    if "body" not in response:
        return ""

    body = response["body"]
    if hasattr(body, "read"):
        raw_bytes = body.read()
        if isinstance(raw_bytes, (bytes, bytearray)):
            return raw_bytes.decode("utf-8", errors="ignore")
        return str(raw_bytes)

    return str(body)


def _extract_summary_from_raw_text(raw_text: str) -> str:
    raw_text = (raw_text or "").strip()
    if not raw_text:
        return ""

    try:
        parsed = json.loads(raw_text)
    except Exception:
        return raw_text

    if isinstance(parsed, str):
        return parsed.strip()

    if isinstance(parsed, dict):
        if parsed.get("content") and isinstance(parsed["content"], list):
            texts = []
            for item in parsed["content"]:
                if isinstance(item, dict) and item.get("text"):
                    texts.append(item["text"])
            if texts:
                return "\n".join(texts).strip()

    return raw_text


def generate_summary(extracted_text: str) -> str:
    """Generate a concise evidence summary from extracted text using Amazon Bedrock."""
    if not extracted_text or not extracted_text.strip():
        logger.info("generate_summary skipped because extracted_text is empty.")
        return "No text available to summarize from the extracted document."

    if not bedrock.client:
        logger.warning("Bedrock client not configured; summary generation skipped.")
        return "Bedrock is not configured. Cannot generate summary at this time."

    text_to_send = extracted_text.strip()
    if len(text_to_send) > MAX_SUMMARY_INPUT_CHARS:
        logger.warning(
            "Extracted text exceeds %d characters; truncating input for Bedrock.",
            MAX_SUMMARY_INPUT_CHARS,
        )
        text_to_send = text_to_send[:MAX_SUMMARY_INPUT_CHARS]

    prompt_text = _build_prompt_text(text_to_send)
    logger.info("Sending summary request to Bedrock converse. input_length=%d", len(text_to_send))

    try:
        resp = bedrock.converse(model_id="amazon.nova-lite-v1:0", input_text=prompt_text)
        raw_text = (resp or {}).get("text", "")
        elapsed = (resp or {}).get("elapsed")
        usage = (resp or {}).get("usage")

        logger.debug("Bedrock raw response: %s", raw_text)
        if elapsed is not None:
            logger.info("Bedrock request completed in %.3fs", elapsed)
        if usage:
            logger.info("Bedrock usage info: %s", usage)

        summary = _extract_summary_from_raw_text(raw_text).strip()
        if not summary:
            logger.warning("Bedrock returned an empty summary.")
            return "Bedrock generated an empty summary."

        logger.info("Bedrock summary generated successfully. summary_length=%d", len(summary))
        return summary
    except ClientError as client_err:
        logger.exception("Bedrock ClientError during summary generation: %s", client_err)
        return "Bedrock service error occurred while generating the summary."
    except Exception as exc:
        logger.exception("Unexpected error during Bedrock summary generation: %s", exc)
        return "Failed to generate summary due to an internal error."
