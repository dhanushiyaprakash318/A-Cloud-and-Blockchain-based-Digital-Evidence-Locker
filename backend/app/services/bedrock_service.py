import json
import re
from typing import Dict, Any, Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


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

            self.client = boto3.client("bedrock-runtime", **client_kwargs)
            print("[BedrockService] Bedrock runtime client initialized")
        except Exception as e:
            print(f"[BedrockService] Failed to initialize Bedrock client: {e}")
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

    def classify_case(self, case_text: str) -> str:
        """
        Send the user text to Amazon Nova Lite via Bedrock Runtime and return the assistant response.
        """
        if not (settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY):
            # Fallback assistant response for local testing when Bedrock is not configured.
            return (
                "I don't have Bedrock access configured right now, but I can still help "
                "with general questions about the case if you provide more details."
            )

        prompt = (
            "You are an AI assistant for a Digital Evidence Management System.\n"
            "Respond directly to the user's query and do not add any protocol or JSON wrappers.\n"
            "Provide a helpful, concise answer based on the provided text.\n\n"
            "User input:\n"
            f"{case_text}\n"
        )

        body = {
            "messages": [
                {"role": "user", "content": [{"text": prompt}]}
            ]
        }

        try:
            response = self.client.invoke_model(
                modelId="amazon.nova-lite-v1:0",
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )

            raw_text = ""
            if "body" in response and hasattr(response["body"], "read"):
                raw_bytes = response["body"].read()
                if isinstance(raw_bytes, bytes):
                    raw_text = raw_bytes.decode("utf-8", errors="ignore")
                else:
                    raw_text = str(raw_bytes)
            else:
                raw_text = str(response.get("body", ""))

            print("[BedrockService] Raw model output:", raw_text)
            assistant_text = self._extract_assistant_text(raw_text)
            return assistant_text

        except ClientError:
            raise
        except Exception as e:
            raise RuntimeError(f"Bedrock assistant failed: {e}")

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


bedrock = BedrockService()
