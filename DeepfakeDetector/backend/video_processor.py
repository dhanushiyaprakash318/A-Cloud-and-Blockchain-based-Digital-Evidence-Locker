import os
import time
from pathlib import Path
from typing import List

import cv2
from PIL import Image


def extract_video_frames(video_path: str, num_frames: int = 16) -> List[Image.Image]:
    if not os.path.exists(video_path):
        raise ValueError('Video file does not exist.')

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise ValueError('Unable to open video file.')

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames <= 0:
        total_frames = 1

    frame_indices = list({int(i) for i in
                          [round(x) for x in __import__('numpy').linspace(0, total_frames - 1, min(num_frames, total_frames))]})
    frames = []

    for frame_index in frame_indices:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        success, frame = cap.read()
        if not success or frame is None:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(frame_rgb))

    cap.release()

    if not frames:
        raise ValueError('Unable to extract frames from the video file.')

    return frames
