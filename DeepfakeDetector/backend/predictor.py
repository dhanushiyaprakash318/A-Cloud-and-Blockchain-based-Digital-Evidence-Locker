import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import torch
from facenet_pytorch import MTCNN
from PIL import Image

from config import (
    EFFICIENTNET_WEIGHTS,
    SWIN_WEIGHTS,
    XCEPTION_WEIGHTS,
    RESNET_WEIGHTS,
    MAX_IMAGE_BYTES,
    MAX_VIDEO_BYTES,
    SUPPORTED_IMAGE_EXTENSIONS,
    SUPPORTED_VIDEO_EXTENSIONS,
)
from models import load_classification_model
from preprocessing import (
    extract_video_frames,
    load_image,
    make_effnet_transform,
    make_swin_transform,
    make_xception_transform,
)
from url_detector import WebsiteRiskDetector

log = logging.getLogger(__name__)


class DeepfakePredictor:
    def __init__(self, device: Optional[str] = None):
        self.device = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))

        self.efficientnet = load_classification_model('efficientnet_b0', EFFICIENTNET_WEIGHTS, self.device)
        self.swin = load_classification_model('swin_base_patch4_window7_224', SWIN_WEIGHTS, self.device)
        self.xception = load_classification_model('xception', XCEPTION_WEIGHTS, self.device)
        self.resnet = load_classification_model('resnet34', RESNET_WEIGHTS, self.device)

        self.effnet_transform = make_effnet_transform()
        self.swin_transform = make_swin_transform()
        self.xception_transform = make_xception_transform()
        self.resnet_transform = self.effnet_transform

        self.face_detector = None
        try:
            self.face_detector = MTCNN(keep_all=True, device=self.device, thresholds=[0.5, 0.6, 0.7], select_largest=False)
        except Exception as exc:
            log.warning(f'Face detector initialization failed: {exc}')

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

    def _detect_faces(self, image: Image.Image) -> List[Image.Image]:
        if self.face_detector is None:
            return []

        boxes, _ = self.face_detector.detect(image)
        faces: List[Image.Image] = []
        if boxes is None:
            return faces

        for box in boxes:
            x1, y1, x2, y2 = [int(max(0, value)) for value in box]
            margin_x = int((x2 - x1) * 0.2)
            margin_y = int((y2 - y1) * 0.2)
            x1 = max(0, x1 - margin_x)
            y1 = max(0, y1 - margin_y)
            x2 = min(image.width, x2 + margin_x)
            y2 = min(image.height, y2 + margin_y)
            faces.append(image.crop((x1, y1, x2, y2)))

        return faces

    def _center_crop(self, image: Image.Image, size: int) -> Image.Image:
        width, height = image.size
        if width < size or height < size:
            return image.resize((size, size), Image.BILINEAR)

        left = (width - size) // 2
        top = (height - size) // 2
        right = left + size
        bottom = top + size
        return image.crop((left, top, right, bottom))

    def _preprocess_faces(self, faces: List[Image.Image]) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
        eff_inputs = torch.stack([self.effnet_transform(face) for face in faces]).to(self.device)
        swin_inputs = torch.stack([self.swin_transform(face) for face in faces]).to(self.device)
        xcp_inputs = torch.stack([self.xception_transform(face) for face in faces]).to(self.device)
        res_inputs = torch.stack([self.resnet_transform(face) for face in faces]).to(self.device)
        return eff_inputs, swin_inputs, xcp_inputs, res_inputs

    def _predict_scores(self, faces: List[Image.Image]) -> Dict[str, float]:
        if not faces:
            return {'efficientnet': 0.0, 'swin': 0.0, 'xception': 0.0, 'resnet': 0.0, 'faces': 0}

        eff_inputs, swin_inputs, xcp_inputs, res_inputs = self._preprocess_faces(faces)
        with torch.no_grad():
            eff_logits = self.efficientnet(eff_inputs)
            swin_logits = self.swin(swin_inputs)
            xcp_logits = self.xception(xcp_inputs)
            res_logits = self.resnet(res_inputs)

        eff_probs = torch.softmax(eff_logits, dim=1)[:, 1].detach().cpu().numpy()
        swin_probs = torch.softmax(swin_logits, dim=1)[:, 1].detach().cpu().numpy()
        xcp_probs = torch.softmax(xcp_logits, dim=1)[:, 1].detach().cpu().numpy()
        res_probs = torch.softmax(res_logits, dim=1)[:, 1].detach().cpu().numpy()

        return {
            'efficientnet': float(np.mean(eff_probs)) if eff_probs.size else 0.0,
            'swin': float(np.mean(swin_probs)) if swin_probs.size else 0.0,
            'xception': float(np.mean(xcp_probs)) if xcp_probs.size else 0.0,
            'resnet': float(np.mean(res_probs)) if res_probs.size else 0.0,
            'faces': len(faces),
        }

    def _ensemble_prediction(self, eff_score: float, swin_score: float, xcp_score: float, resnet_score: float) -> Tuple[float, str]:
        final_score = 0.25 * eff_score + 0.25 * swin_score + 0.25 * xcp_score + 0.25 * resnet_score
        prediction = 'FAKE' if final_score >= 0.5 else 'REAL'
        return final_score, prediction

    def _build_media_response(
        self,
        prediction: str,
        eff_score: float,
        swin_score: float,
        xcp_score: float,
        resnet_score: float,
        faces: int,
        frames: Optional[int],
        processing_time: float,
    ) -> Dict[str, object]:
        final_score = 0.25 * eff_score + 0.25 * swin_score + 0.25 * xcp_score + 0.25 * resnet_score
        confidence_pct = round(float(final_score * 100), 1)
        return {
            'prediction': prediction,
            'confidence': confidence_pct,
            'efficientnet_score': round(float(eff_score * 100), 1),
            'swin_score': round(float(swin_score * 100), 1),
            'xception_score': round(float(xcp_score * 100), 1),
            'resnet_score': round(float(resnet_score * 100), 1),
            'media_type': 'video' if frames is not None else 'image',
            'faces_detected': faces,
            'frames_analyzed': frames,
            'processing_time': f'{processing_time:.2f} sec',
        }

    def predict_image(self, image_path: str) -> Dict[str, object]:
        self._validate_file(image_path, SUPPORTED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        start = time.time()
        image = load_image(image_path)
        faces = self._detect_faces(image)
        if not faces:
            faces = [self._center_crop(image, 299)]

        scores = self._predict_scores(faces)
        _, prediction = self._ensemble_prediction(scores['efficientnet'], scores['swin'], scores['xception'], scores['resnet'])
        return self._build_media_response(
            prediction=prediction,
            eff_score=scores['efficientnet'],
            swin_score=scores['swin'],
            xcp_score=scores['xception'],
            resnet_score=scores['resnet'],
            faces=scores['faces'],
            frames=None,
            processing_time=time.time() - start,
        )

    def predict_video(self, video_path: str) -> Dict[str, object]:
        self._validate_file(video_path, SUPPORTED_VIDEO_EXTENSIONS, MAX_VIDEO_BYTES)
        start = time.time()
        frames = extract_video_frames(video_path, num_frames=16)
        if not frames:
            raise ValueError('No valid video frames could be extracted.')

        faces: List[Image.Image] = []
        for frame in frames:
            faces.extend(self._detect_faces(frame))

        if not faces:
            faces = [self._center_crop(frame, 299) for frame in frames[:4]]

        scores = self._predict_scores(faces)
        _, prediction = self._ensemble_prediction(scores['efficientnet'], scores['swin'], scores['xception'], scores['resnet'])
        response = self._build_media_response(
            prediction=prediction,
            eff_score=scores['efficientnet'],
            swin_score=scores['swin'],
            xcp_score=scores['xception'],
            resnet_score=scores['resnet'],
            faces=scores['faces'],
            frames=len(frames),
            processing_time=time.time() - start,
        )
        return response

    def predict_website(self, url: str) -> Dict[str, object]:
        return self.url_detector.analyze_website(url)
