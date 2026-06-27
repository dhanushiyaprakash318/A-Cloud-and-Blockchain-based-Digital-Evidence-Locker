import os
import re
import uuid
import json
import shutil
import boto3
import torch
import validators
import tempfile
import numpy as np
import cv2
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from PIL import Image
from typing import Any, Dict, List, Optional, Tuple
from torchvision import transforms
from torchvision.transforms import functional as TF
import timm
from facenet_pytorch import MTCNN
from utils.url_loader import download_from_url

SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
MAX_IMAGE_BYTES = 30 * 1024 * 1024
MAX_VIDEO_BYTES = 200 * 1024 * 1024


def _to_decimal(value: Any) -> Any:
    if isinstance(value, float):
        return Decimal(str(round(value, 6)))
    if isinstance(value, dict):
        return {k: _to_decimal(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_decimal(v) for v in value]
    return value


class DeepfakeService:
    def __init__(self, device: Optional[str] = None):
        self.device = torch.device(device or ('cuda' if torch.cuda.is_available() else 'cpu'))
        self.temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp_uploads')
        os.makedirs(self.temp_dir, exist_ok=True)

        self.effnet = self._load_efficientnet()
        self.xception = self._load_xception()
        self.face_detector = self._build_face_detector()

        self.preprocess_effnet = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self.preprocess_xception = transforms.Compose([
            transforms.Resize((299, 299)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

        self.dynamodb_table_name = os.getenv('DYNAMODB_TABLE_DEEPFAKE', 'deepfake-results')
        self.dynamodb_table = self._init_dynamodb_table()
        self.local_results_path = os.path.join(self.temp_dir, 'deepfake_results.json')
        if not os.path.exists(self.local_results_path):
            with open(self.local_results_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2)

    def _build_face_detector(self) -> MTCNN:
        return MTCNN(keep_all=True, device=self.device, thresholds=[0.6, 0.7, 0.7], select_largest=False)

    def _load_efficientnet(self):
        model = timm.create_model('efficientnet_b4', pretrained=True, num_classes=2)
        weights_path = os.getenv('EFFNET_B4_WEIGHTS_PATH', '')
        if weights_path and os.path.exists(weights_path):
            try:
                state_dict = torch.load(weights_path, map_location=self.device)
                model.load_state_dict(state_dict)
                print(f"Loaded EfficientNet-B4 weights from {weights_path}")
            except Exception as exc:
                print(f"Failed to load EfficientNet-B4 weights from {weights_path}: {exc}")
        model = model.to(self.device)
        model.eval()
        return model

    def _load_xception(self):
        model = timm.create_model('xception', pretrained=True, num_classes=2)
        weights_path = os.getenv('XCEPTION_WEIGHTS_PATH', '')
        if weights_path and os.path.exists(weights_path):
            try:
                state_dict = torch.load(weights_path, map_location=self.device)
                model.load_state_dict(state_dict)
                print(f"Loaded Xception weights from {weights_path}")
            except Exception as exc:
                print(f"Failed to load Xception weights from {weights_path}: {exc}")
        model = model.to(self.device)
        model.eval()
        return model

    def _init_dynamodb_table(self):
        aws_key = os.getenv('AWS_ACCESS_KEY_ID')
        aws_secret = os.getenv('AWS_SECRET_ACCESS_KEY')
        aws_region = os.getenv('AWS_REGION', 'us-east-1')

        if not aws_key or not aws_secret:
            print('DeepfakeService: AWS credentials not configured. Using local fallback storage.')
            return None

        try:
            boto_kwargs = {
                'region_name': aws_region,
                'aws_access_key_id': aws_key,
                'aws_secret_access_key': aws_secret,
            }
            aws_session_token = os.getenv('AWS_SESSION_TOKEN')
            if aws_session_token:
                boto_kwargs['aws_session_token'] = aws_session_token

            dynamodb = boto3.resource('dynamodb', **boto_kwargs)
            table = dynamodb.Table(self.dynamodb_table_name)
            table.load()
            print(f"Connected to DynamoDB deepfake table: {self.dynamodb_table_name}")
            return table
        except Exception as exc:
            print(f"DeepfakeService: Unable to connect to DynamoDB table {self.dynamodb_table_name}: {exc}")
            return None

    def _validate_file(self, file_path: str, allowed_exts: set, max_size: int):
        ext = Path(file_path).suffix.lower()
        if ext not in allowed_exts:
            raise ValueError(f"Unsupported file type: {ext}. Allowed types: {', '.join(sorted(allowed_exts))}")
        size = os.path.getsize(file_path)
        if size == 0:
            raise ValueError('Uploaded file is empty.')
        if size > max_size:
            raise ValueError(f'File too large. Must be smaller than {max_size // (1024*1024)} MB.')

    def _load_image(self, file_path: str) -> Image.Image:
        try:
            image = Image.open(file_path).convert('RGB')
        except Exception as exc:
            raise ValueError(f'Unable to open image: {exc}')
        return image

    def _detect_faces(self, image: Image.Image) -> List[Image.Image]:
        boxes, _ = self.face_detector.detect(image)
        faces: List[Image.Image] = []
        if boxes is None:
            return faces

        for box in boxes:
            x1, y1, x2, y2 = [int(max(0, v)) for v in box]
            margin_x = int((x2 - x1) * 0.2)
            margin_y = int((y2 - y1) * 0.2)
            x1 = max(0, x1 - margin_x)
            y1 = max(0, y1 - margin_y)
            x2 = min(image.width, x2 + margin_x)
            y2 = min(image.height, y2 + margin_y)
            faces.append(image.crop((x1, y1, x2, y2)))

        return faces

    def _center_crop(self, image: Image.Image, size: int) -> Image.Image:
        if image.width < size or image.height < size:
            return image.resize((size, size), Image.BILINEAR)
        return TF.center_crop(image, size)

    def _preprocess(self, face: Image.Image) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.preprocess_effnet(face), self.preprocess_xception(face)

    def _predict_faces(self, faces: List[Image.Image]) -> Dict[str, float]:
        if not faces:
            return {'efficientnet': 0.0, 'xception': 0.0}

        eff_tensors = torch.stack([self.preprocess_effnet(face) for face in faces]).to(self.device)
        xcp_tensors = torch.stack([self.preprocess_xception(face) for face in faces]).to(self.device)

        with torch.no_grad():
            eff_logits = self.effnet(eff_tensors)
            xcp_logits = self.xception(xcp_tensors)

        eff_probs = torch.softmax(eff_logits, dim=1)[:, 1].detach().cpu().numpy()
        xcp_probs = torch.softmax(xcp_logits, dim=1)[:, 1].detach().cpu().numpy()

        return {
            'efficientnet': float(np.mean(eff_probs)) if eff_probs.size else 0.0,
            'xception': float(np.mean(xcp_probs)) if xcp_probs.size else 0.0,
            'faces': len(faces),
        }

    def _ensemble_predict(self, eff_score: float, xcp_score: float) -> Tuple[float, str]:
        score = 0.55 * eff_score + 0.45 * xcp_score
        if score >= 0.62:
            return score, 'Fake'
        if score <= 0.38:
            return score, 'Real'
        return score, 'Suspicious'

    def _frame_path_to_type(self, file_path: str) -> str:
        ext = Path(file_path).suffix.lower()
        if ext in SUPPORTED_IMAGE_EXTENSIONS:
            return 'image'
        if ext in SUPPORTED_VIDEO_EXTENSIONS:
            return 'video'
        return 'unknown'

    def _extract_video_frames(self, video_path: str, num_frames: int = 16) -> List[Image.Image]:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError('Unable to open video file for analysis.')

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 1
        indices = np.linspace(0, total_frames - 1, min(num_frames, total_frames), dtype=int)

        frames: List[Image.Image] = []
        for frame_index in indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, int(frame_index))
            ret, frame = cap.read()
            if not ret:
                continue
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(Image.fromarray(frame_rgb))

        cap.release()
        return frames

    def _prepare_response(self, file_path: str, media_type: str, eff: float, xcp: float, prediction: str, frames: int, faces: int, source_url: Optional[str] = None) -> Dict[str, Any]:
        response = {
            'id': str(uuid.uuid4()),
            'filename': Path(file_path).name,
            'media_type': media_type,
            'prediction': prediction,
            'confidence': round(float((0.55 * eff + 0.45 * xcp) * 100), 1),
            'efficientnet_score': round(float(eff * 100), 1),
            'xception_score': round(float(xcp * 100), 1),
            'frames_analyzed': frames if media_type == 'video' else None,
            'faces_detected': faces,
            'source_url': source_url,
            'uploaded_at': datetime.utcnow().isoformat() + 'Z',
        }
        return response

    def _save_result(self, record: Dict[str, Any]):
        if self.dynamodb_table:
            try:
                dynamo_record = {k: _to_decimal(v) if v is not None else v for k, v in record.items()}
                self.dynamodb_table.put_item(Item=dynamo_record)
                return
            except Exception as exc:
                print(f'DeepfakeService: DynamoDB save failed, falling back to local file: {exc}')

        with open(self.local_results_path, 'r+', encoding='utf-8') as f:
            data = json.load(f)
            data.append(record)
            f.seek(0)
            json.dump(data, f, indent=2)
            f.truncate()

    def predict_image(self, image_path: str) -> Dict[str, Any]:
        self._validate_file(image_path, SUPPORTED_IMAGE_EXTENSIONS, MAX_IMAGE_BYTES)
        image = self._load_image(image_path)
        faces = self._detect_faces(image)
        if not faces:
            faces = [self._center_crop(image, 299)]

        scores = self._predict_faces(faces)
        confidence, prediction = self._ensemble_predict(scores['efficientnet'], scores['xception'])
        response = self._prepare_response(
            file_path=image_path,
            media_type='image',
            eff=scores['efficientnet'],
            xcp=scores['xception'],
            prediction=prediction,
            frames=0,
            faces=scores['faces'],
            source_url=None,
        )
        self._save_result(response)
        return response

    def predict_video(self, video_path: str) -> Dict[str, Any]:
        self._validate_file(video_path, SUPPORTED_VIDEO_EXTENSIONS, MAX_VIDEO_BYTES)
        frames = self._extract_video_frames(video_path, num_frames=16)
        if not frames:
            raise ValueError('Video contains no readable frames.')

        faces: List[Image.Image] = []
        for frame in frames:
            faces.extend(self._detect_faces(frame))

        if not faces:
            fallback_faces = [self._center_crop(frame, 299) for frame in frames[:4]]
            faces = fallback_faces

        scores = self._predict_faces(faces)
        confidence, prediction = self._ensemble_predict(scores['efficientnet'], scores['xception'])
        response = self._prepare_response(
            file_path=video_path,
            media_type='video',
            eff=scores['efficientnet'],
            xcp=scores['xception'],
            prediction=prediction,
            frames=len(frames),
            faces=scores['faces'],
            source_url=None,
        )
        self._save_result(response)
        return response

    def predict_url(self, url: str) -> Dict[str, Any]:
        if not validators.url(url):
            raise ValueError('Invalid URL. Please provide a valid image or video URL.')

        result = download_from_url(url, save_dir=self.temp_dir)
        if result.get('error'):
            raise ValueError(result['error'])

        file_path = result.get('file_path')
        if not file_path or not os.path.exists(file_path):
            raise ValueError('URL did not resolve to a supported media file.')

        media_type = self._frame_path_to_type(file_path)
        if media_type == 'image':
            response = self.predict_image(file_path)
        elif media_type == 'video':
            response = self.predict_video(file_path)
        else:
            raise ValueError('Downloaded URL is not a supported image or video format.')

        response['source_url'] = url
        self._save_result(response)
        return response

    def cleanup_temp(self):
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)
