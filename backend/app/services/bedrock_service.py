"""Bedrock runtime wrapper using the Converse API (boto3).

This module provides a small helper service that initializes a boto3
`bedrock-runtime` client and exposes a `converse` method which is suitable
for Nova family models. It centralizes logging, error handling and response
parsing so other services (ai_summary, chat_assistant) can reuse it.
"""

import json
import re
import time
import logging
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from app.core.config import settings

logger = logging.getLogger(__name__)


class BedrockService:
    def __init__(self):
        self.client: Optional[any] = None
        try:
            client_kwargs = {"region_name": settings.AWS_REGION}
            # Only include explicit credentials when configured in settings
            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                client_kwargs.update({
                    "aws_access_key_id": settings.AWS_ACCESS_KEY_ID,
                    "aws_secret_access_key": settings.AWS_SECRET_ACCESS_KEY,
                })
                if settings.AWS_SESSION_TOKEN:
                    client_kwargs["aws_session_token"] = settings.AWS_SESSION_TOKEN

            # Use the Bedrock runtime client which exposes the Converse API
            self.client = boto3.client("bedrock-runtime", **client_kwargs)
            logger.info("Bedrock runtime client initialized for region=%s", settings.AWS_REGION)
        except Exception as e:
            logger.exception("Failed to initialize Bedrock client: %s", e)
            self.client = None

    def _extract_json(self, text: str) -> Dict[str, Any]:
        text = (text or "").strip()
        try:
            return json.loads(text)
        except Exception:
            # fallback: try to extract first JSON object
            m = re.search(r"(\{.*\})", text, re.DOTALL)
            if not m:
                raise ValueError("Model did not return valid JSON")
            try:
                return json.loads(m.group(1))
            except Exception:
                raise ValueError("Model returned malformed JSON")

    def _extract_assistant_text(self, raw_text: str) -> str:
        raw_text = (raw_text or "").strip()
        if not raw_text:
            return ""

        try:
            parsed = json.loads(raw_text)
        except Exception:
            # If response is plain text, return it directly.
            return raw_text

        def find_text(obj):
            if isinstance(obj, str):
                return obj
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key == "text" and isinstance(value, str):
                        return value
                    result = find_text(value)
                    if result:
                        return result
            if isinstance(obj, list):
                for item in obj:
                    result = find_text(item)
                    if result:
                        return result
            return None

        found = find_text(parsed)
        return found.strip() if isinstance(found, str) else raw_text

    def converse(self, model_id: str, input_text: Optional[str] = None, system: Optional[str] = None, messages: Optional[list] = None) -> Dict[str, Any]:
        if not self.client:
            raise RuntimeError("Bedrock client is not initialized")

        model = model_id
        # Build kwargs for the Converse API call per requested syntax
        call_kwargs: Dict[str, Any] = {"modelId": model}

        if system is not None:
            # Converse API expects system as a list of text blocks: [{'text': SYSTEM_PROMPT}]
            call_kwargs["system"] = [{"text": system}]

        if messages is not None:
            # Assume caller provided correctly-shaped messages; however, sanitize
            # any inner content entries to remove legacy 'type' keys if present.
            sanitized_msgs = []
            for m in messages:
                if not isinstance(m, dict):
                    continue
                role = m.get("role")
                content = m.get("content") if isinstance(m.get("content"), list) else []
                new_content = []
                for c in content:
                    if isinstance(c, dict) and "text" in c:
                        new_content.append({"text": c.get("text")})
                sanitized_msgs.append({"role": role, "content": new_content})
            call_kwargs["messages"] = sanitized_msgs
        else:
            # If messages not provided, construct a single user message from input_text
            call_kwargs["messages"] = [
                {
                    "role": "user",
                    "content": [{"text": input_text or ""}],
                }
            ]

        logger.info("Bedrock converse request starting: model=%s input_length=%d system_provided=%s messages_count=%d", model, len(input_text or ""), bool(system), len(call_kwargs.get("messages", [])))
        start = time.time()
        try:
            # Use the Converse API without body/contentType/accept params
            response = self.client.converse(**call_kwargs)

            elapsed = time.time() - start

            # Response format per Converse API: response['output']['message']['content'][0]['text']
            out_text = None
            try:
                out = response.get("output", {})
                msg = out.get("message") if isinstance(out, dict) else None
                if isinstance(msg, dict):
                    contents = msg.get("content")
                    if isinstance(contents, list) and len(contents) > 0:
                        first = contents[0]
                        out_text = first.get("text") if isinstance(first, dict) else None
            except Exception:
                out_text = None

            # Fallback: try to read raw body if present
            if not out_text:
                raw_text = ""
                if "body" in response and hasattr(response["body"], "read"):
                    raw_bytes = response["body"].read()
                    raw_text = raw_bytes.decode("utf-8", errors="ignore") if isinstance(raw_bytes, (bytes, bytearray)) else str(raw_bytes)
                else:
                    raw_text = str(response.get("body", ""))
                out_text = raw_text

            # Token usage may be present elsewhere in response — attempt to extract
            usage = None
            try:
                if isinstance(response, dict):
                    usage = response.get("usage")
            except Exception:
                usage = None

            logger.info("Bedrock converse completed: model=%s elapsed=%.3fs", model, elapsed)
            if usage:
                logger.debug("Bedrock token usage: %s", usage)

            return {"text": out_text or "", "usage": usage, "elapsed": elapsed, "model": model}

        except ClientError as ce:
            logger.exception("Bedrock ClientError calling converse for model=%s: %s", model, ce)
            raise
        except BotoCoreError as be:
            logger.exception("Bedrock BotoCoreError calling converse for model=%s: %s", model, be)
            raise
        except Exception as exc:
            logger.exception("Unexpected error calling Bedrock converse for model=%s: %s", model, exc)
            raise
            logger.exception("Bedrock ClientError calling converse for model=%s: %s", model, ce)
            raise
        except BotoCoreError as be:
            logger.exception("Bedrock BotoCoreError calling converse for model=%s: %s", model, be)
            raise
        except Exception as exc:
            logger.exception("Unexpected error calling Bedrock converse for model=%s: %s", model, exc)
            raise


bedrock = BedrockService()
