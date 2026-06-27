import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse

from predictor import DeepfakePredictor
from schemas import MediaPredictionResponse, WebsitePredictionResponse, HealthResponse

log = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path(__file__).resolve().parent / 'temp_uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def save_upload_file(upload_file: UploadFile, target_dir: Path) -> str:
    extension = Path(upload_file.filename or '').suffix.lower()
    if not extension:
        raise ValueError('Uploaded file must contain an extension.')

    target_path = target_dir / f"{uuid4()}{extension}"
    with open(target_path, 'wb') as buffer:
        shutil.copyfileobj(upload_file.file, buffer)
    return str(target_path)


@router.post('/predict/image', response_model=MediaPredictionResponse)
async def predict_image(request: Request, file: UploadFile = File(...)):
    file_path = None
    predictor: DeepfakePredictor = request.app.state.predictor
    log.info('Incoming Request: image prediction')
    try:
        file_path = save_upload_file(file, UPLOAD_DIR)
        log.info('Processing Started: image')
        result = predictor.predict_image(file_path)
        log.info(
            f"Prediction: {result['prediction']} Confidence: {result['confidence']} EfficientNet: {result['efficientnet_score']} "
            f"Swin: {result['swin_score']} Xception: {result['xception_score']} Processing Time: {result['processing_time']}"
        )
        return JSONResponse(content=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        log.exception('Unexpected error during image prediction')
        raise HTTPException(status_code=500, detail='Internal server error during image prediction.')
    finally:
        if file_path and Path(file_path).exists():
            Path(file_path).unlink(missing_ok=True)


@router.post('/predict/video', response_model=MediaPredictionResponse)
async def predict_video(request: Request, file: UploadFile = File(...)):
    file_path = None
    predictor: DeepfakePredictor = request.app.state.predictor
    log.info('Incoming Request: video prediction')
    try:
        file_path = save_upload_file(file, UPLOAD_DIR)
        log.info('Processing Started: video')
        result = predictor.predict_video(file_path)
        log.info(
            f"Prediction: {result['prediction']} Confidence: {result['confidence']} EfficientNet: {result['efficientnet_score']} "
            f"Swin: {result['swin_score']} Xception: {result['xception_score']} Processing Time: {result['processing_time']}"
        )
        return JSONResponse(content=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        log.exception('Unexpected error during video prediction')
        raise HTTPException(status_code=500, detail='Internal server error during video prediction.')
    finally:
        if file_path and Path(file_path).exists():
            Path(file_path).unlink(missing_ok=True)


@router.post('/predict/url', response_model=WebsitePredictionResponse)
async def predict_url(request: Request, url: str = Form(...)):
    predictor: DeepfakePredictor = request.app.state.predictor
    log.info('Incoming Request: URL prediction')
    try:
        log.info(f'Processing Started: URL ({url})')
        result = predictor.predict_website(url)
        log.info(
            f"Classification: {result['classification']} Confidence: {result['confidence']} "
            f"Risk Score: {result['risk_score']} Reason: {result['reason']}"
        )
        return JSONResponse(content=result)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception:
        log.exception('Unexpected error during URL prediction')
        raise HTTPException(status_code=500, detail='Internal server error during URL prediction.')


@router.get('/health', response_model=HealthResponse)
def health_check(request: Request):
    predictor: DeepfakePredictor = request.app.state.predictor
    return {
        'status': 'online',
        'service': 'Deepfake Detection Service',
        'device': str(predictor.device),
        'models': ['EfficientNet-B0', 'Swin Transformer', 'Xception', 'ResNet-34'],
    }
