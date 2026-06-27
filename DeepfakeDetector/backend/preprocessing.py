import os
from pathlib import Path
from typing import List

import cv2
import numpy as np
from PIL import Image
from torchvision import transforms

SUPPORTED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
SUPPORTED_VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
MAX_IMAGE_BYTES = 30 * 1024 * 1024
MAX_VIDEO_BYTES = 200 * 1024 * 1024


def make_effnet_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def make_swin_transform():
    return transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def make_xception_transform():
    return transforms.Compose([
        transforms.Resize((299, 299)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])


def is_image_path(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS


def is_video_path(path: str) -> bool:
    return Path(path).suffix.lower() in SUPPORTED_VIDEO_EXTENSIONS


def load_image(path: str) -> Image.Image:
    try:
        image = Image.open(path).convert('RGB')
    except Exception as exc:
        raise ValueError(f"Unable to open image: {exc}")
    return image


def extract_video_frames(video_path: str, num_frames: int = 16) -> List[Image.Image]:
    if not os.path.exists(video_path):
        raise ValueError("Video file does not exist.")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError('Unable to open video file for analysis.')

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 1

    frame_indices = np.linspace(0, total_frames - 1, min(num_frames, total_frames), dtype=int)
    frames = []

    for index in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(index))
        success, frame = cap.read()
        if not success:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(frame_rgb))

    cap.release()

    if not frames:
        raise ValueError('Unable to extract frames from the video.')

    return frames
