from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from botocore.exceptions import ClientError

from app.services.bedrock_service import bedrock

router = APIRouter()


class ClassifyRequest(BaseModel):
    case_text: str


@router.post('/classify')
async def classify_case(req: ClassifyRequest):
    if not req.case_text or not req.case_text.strip():
        raise HTTPException(status_code=400, detail='case_text is required')

    try:
        try:
            assistant_response = bedrock.classify_case(req.case_text)
        except ClientError:
            raise
        except Exception as e:
            print(f"[Bedrock API] Bedrock service error: {e}")
            assistant_response = (
                "I'm sorry, I couldn't reach the AI assistant right now. "
                "Please try again later or provide more details."
            )

        return {
            'success': True,
            'assistant_response': assistant_response
        }

    except ClientError as e:
        # AWS client errors
        code = e.response.get('Error', {}).get('Code', '')
        if code == 'AccessDeniedException' or code == 'AccessDenied':
            raise HTTPException(status_code=403, detail='Access to Bedrock denied')
        if code == 'ValidationException':
            raise HTTPException(status_code=422, detail='Invalid request to Bedrock')
        raise HTTPException(status_code=502, detail=f'Bedrock client error: {code}')

    except ValueError as ve:
        # Invalid JSON or unexpected classification
        raise HTTPException(status_code=502, detail=str(ve))
    except RuntimeError as re:
        # client not configured
        raise HTTPException(status_code=503, detail=str(re))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f'Internal error: {e}')
