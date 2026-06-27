from pydantic import BaseModel
from typing import Optional


class MediaPredictionResponse(BaseModel):
    prediction: str
    confidence: float
    efficientnet_score: float
    swin_score: float
    xception_score: float
    resnet_score: float
    media_type: str
    faces_detected: Optional[int] = None
    frames_analyzed: Optional[int] = None
    processing_time: str


class WebsitePredictionResponse(BaseModel):
    classification: str
    confidence: float
    risk_score: int
    reason: str
    hostname: Optional[str] = None
    is_https: bool


class HealthResponse(BaseModel):
    status: str
    service: str
    device: str
    models: list[str]
