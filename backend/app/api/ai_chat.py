from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from botocore.exceptions import ClientError

from app.services.bedrock_service import bedrock
from app.services.prompt_builder import prompt_builder
from app.services.retrieval_service import retrieval_service
from app.core.config import settings

router = APIRouter()


class AIChatRequest(BaseModel):
    question: str


@router.post("/query")
async def query_ai(request: AIChatRequest):
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="question is required")

    try:
        retrieval_context = retrieval_service.retrieve(request.question)
        intent = retrieval_context.get("intent")

        # Short-circuit for simple counts to guarantee exact DB answers
        if intent == "count_cases":
            count = int(retrieval_context.get("summary", {}).get("count", 0))
            answer = f"There are {count} cases under investigation."

            # Still build the prompt and send to Bedrock for logging/auditing, but do not wait on it
            try:
                prompt = prompt_builder.build_prompt(request.question, retrieval_context)
                raw_response = bedrock.classify_case(prompt)
            except Exception as e:
                raw_response = str(e)

            return {
                "success": True,
                "answer": answer,
                "raw_response": raw_response,
                "retrieval_context": retrieval_context,
            }

        # Handle search_accused (e.g., "List all absconding accused") with exact DB results
        if intent == "search_accused":
            accused = retrieval_context.get("accused", []) or []
            if not accused:
                return {
                    "success": True,
                    "answer": "I couldn't find that information in the Divel database.",
                    "retrieval_context": retrieval_context,
                }

            # Build a concise, factual answer listing the accused and case references
            lines = []
            for a in accused:
                name = a.get("name") or "Unknown"
                status = a.get("status") or "Unknown"
                case_num = a.get("caseNumber") or a.get("case_id") or "Unknown case"
                brief = f"{name} — {status} (Case: {case_num})"
                lines.append(brief)

            answer = "List of accused matching your query:\n" + "\n".join(lines)

            # Send context to Bedrock for optional summarization/audit but return exact DB answer
            try:
                prompt = prompt_builder.build_prompt(request.question, retrieval_context)
                raw_response = bedrock.classify_case(prompt)
            except Exception as e:
                raw_response = str(e)

            return {
                "success": True,
                "answer": answer,
                "raw_response": raw_response,
                "retrieval_context": retrieval_context,
            }

        # Handle search_case: return all matching cases as factual DB-backed blocks
        if intent == "search_case":
            cases = retrieval_context.get("cases", []) or []
            if not cases:
                return {
                    "success": True,
                    "answer": "I couldn't find that information in the Divel database.",
                    "retrieval_context": retrieval_context,
                }

            def fmt_case(c: dict) -> str:
                lines = [
                    f"Case Number: {c.get('caseNumber', 'Unknown')}",
                    f"Status: {c.get('status', 'Unknown')}",
                    f"District: {c.get('district', 'Unknown')}",
                    f"Unit: {c.get('unit', 'Unknown')}",
                    f"Date Of Offence: {c.get('dateOfOffence', 'Unknown')}",
                    f"Date Of Report: {c.get('dateOfReport', 'Unknown')}",
                    f"Scene Of Crime: {c.get('sceneOfCrime', 'Unknown')}",
                    f"Law Sections: {', '.join(c.get('lawSections') or []) if c.get('lawSections') else 'N/A'}",
                    f"Description: {c.get('description') or 'N/A'}",
                    f"Custom Fields: {c.get('customFields') or []}",
                ]
                return "\n".join(lines)

            blocks = [fmt_case(c) for c in cases]
            answer = "\n\n".join(blocks)

            # Optional: still send to Bedrock for audit but return DB answer
            try:
                prompt = prompt_builder.build_prompt(request.question, retrieval_context)
                raw_response = bedrock.classify_case(prompt)
            except Exception as e:
                raw_response = str(e)

            return {
                "success": True,
                "answer": answer,
                "raw_response": raw_response,
                "retrieval_context": retrieval_context,
            }

        prompt = prompt_builder.build_prompt(request.question, retrieval_context)
        response_text = bedrock.classify_case(prompt)

        if not retrieval_context.get("data_found"):
            fallback_mode = getattr(settings, "AI_FALLBACK_MODE", "hybrid")
            if fallback_mode == "strict":
                return {
                    "success": True,
                    "answer": "I couldn't find that information in the Divel database.",
                    "raw_response": response_text,
                    "retrieval_context": retrieval_context,
                    "answer_source": "db",
                }

            # hybrid or general: use Bedrock/LLM to answer, but mark with a visible disclaimer
            try:
                llm_text = response_text
            except Exception:
                llm_text = ""

            disclaimer = (
                "[Disclaimer] This response was generated by the LLM and may include information outside the Divel database. "
                "Verify facts against official records."
            )
            answer = f"{disclaimer}\n\n{llm_text}" if llm_text else disclaimer

            return {
                "success": True,
                "answer": answer,
                "raw_response": response_text,
                "retrieval_context": retrieval_context,
                "answer_source": "llm",
            }

        return {
            "success": True,
            "answer": response_text,
            "retrieval_context": retrieval_context,
        }
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in {"AccessDeniedException", "AccessDenied"}:
            raise HTTPException(status_code=403, detail="Access to Bedrock denied")
        if code == "ValidationException":
            raise HTTPException(status_code=422, detail="Invalid request to Bedrock")
        raise HTTPException(status_code=502, detail=f"Bedrock client error: {code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
