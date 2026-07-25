import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional

import torch
from PIL import Image
from transformers import pipeline

from config import (
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
)
from preprocessing import extract_video_frames, load_image
from url_detector import WebsiteRiskDetector

log = logging.getLogger(__name__)

DEEPFAKE_MODEL_ID = 'dima806/deepfake_vs_real_image_detection'


class DeepfakePredictor:
    def __init__(self, device: Optional[str] = None):
        self.device = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))

        # The pretrained ViT classifier expects whole images (it does its own resize/normalize
        # via the model's image processor). Feeding it externally cropped/aligned face regions
        # pushes inputs out of the training distribution and collapses every verdict to FAKE, so
        # we classify the full image (and full sampled video frames) directly.
        self.classifier = pipeline(
            'image-classification',
            model=DEEPFAKE_MODEL_ID,
            device=0 if self.device.type == 'cuda' else -1,
        )

        self.url_detector = WebsiteRiskDetector()
        self.temp_dir = Path(__file__).resolve().parent / 'temp_uploads'
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def _validate_file(self, file_path: str, allowed_exts: set, max_size: int):
        if not os.path.exists(file_path):
            raise ValueError('File not found.')

        ext = Path(file_path).suffix.lower()
        if ext not in allowed_exts:
            raise ValueError(f'Unsupported file type: {ext}.')

        file_size = os.path.getsize(file_path)
        if file_size == 0:
            raise ValueError('Uploaded file is empty.')
        if file_size > max_size:
            raise ValueError(f'File size exceeds the limit of {max_size // (1024 * 1024)} MB.')

    def _fake_score_for_image(self, image: Image.Image) -> Optional[float]:
        """Return the classifier's 'fake' probability for a single image, or None on failure."""
        try:
            results = self.classifier(image)
        except Exception as exc:
            log.warning(f'Classifier inference failed: {exc}')
            return None

        scores_by_label = {str(r['label']).strip().lower(): float(r['score']) for r in results}
        if 'fake' in scores_by_label:
            return scores_by_label['fake']
        if 'real' in scores_by_label:
            return 1.0 - scores_by_label['real']
        return None

    def _build_media_response(
        self,
        fake_score: float,
        frames: Optional[int],
        processing_time: float,
    ) -> Dict[str, object]:
        prediction = 'FAKE' if fake_score >= 0.5 else 'REAL'
        fake_pct = round(float(fake_score * 100), 1)
        return {
            'prediction': prediction,
            'confidence': fake_pct,
            # Single-model score duplicated across the legacy per-model fields to keep the API response shape stable.
            'efficientnet_score': fake_pct,
            'swin_score': fake_pct,
            'xception_score': fake_pct,
            'resnet_score': fake_pct,
            'media_type': 'video' if frames is not None else 'image',
            'faces_detected': None,
            'frames_analyzed': frames,
            'processing_time': f'{processing_time:.2f} sec',
        }

    def predict_image(self, image_path: str) -> Dict[str, object]:
        self._validate_file(image_path, SUPPORTED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        start = time.time()
        image = load_image(image_path)
        fake_score = self._fake_score_for_image(image)
        if fake_score is None:
            raise ValueError('Unable to classify the provided image.')
        return self._build_media_response(
            fake_score=fake_score,
            frames=None,
            processing_time=time.time() - start,
        )

    def predict_video(self, video_path: str) -> Dict[str, object]:
        self._validate_file(video_path, SUPPORTED_VIDEO_EXTENSIONS, MAX_VIDEO_BYTES)
        start = time.time()
        frames = extract_video_frames(video_path, num_frames=16)
        if not frames:
            raise ValueError('No valid video frames could be extracted.')

        fake_scores = [s for s in (self._fake_score_for_image(frame) for frame in frames) if s is not None]
        if not fake_scores:
            raise ValueError('Unable to classify any frames of the provided video.')

        return self._build_media_response(
            fake_score=sum(fake_scores) / len(fake_scores),
            frames=len(frames),
            processing_time=time.time() - start,
        )

    def predict_website(self, url: str) -> Dict[str, object]:
        return self.url_detector.analyze_website(url)
