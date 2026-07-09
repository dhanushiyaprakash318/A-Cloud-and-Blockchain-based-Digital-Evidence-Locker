from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.query_router import route as query_route

router = APIRouter()


class AssistantChatRequest(BaseModel):
    case_id: str
    question: str


class AssistantChatResponse(BaseModel):
    answer: str


@router.post("/chat", response_model=AssistantChatResponse)
async def chat_assistant(request: AssistantChatRequest):
    """Answer investigator questions using only stored evidence summaries."""
    if not request.case_id or not request.case_id.strip():
        raise HTTPException(status_code=400, detail="case_id is required")
    if not request.question or not request.question.strip():
        raise HTTPException(status_code=400, detail="question is required")

    try:
        result = query_route(request.question.strip(), request.case_id.strip())
        # `result` is expected to contain keys `intent` and `answer`.
        return {"answer": result.get("answer", "")}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Internal error: {exc}")
