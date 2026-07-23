import cv2
import torch
import numpy as np
from PIL import Image
from facenet_pytorch import MTCNN

class FaceDetector:
    def __init__(self, device='cpu'):
        # MTCNN for face detection
        self.device = device
        self.mtcnn = MTCNN(keep_all=True, device=self.device, select_largest=False)

    def detect_faces(self, image_input):
        """
        Detect faces in an image (numpy array or PIL Image).
        Returns a list of PIL Images cropped to the face.
        """
        if isinstance(image_input, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        else:
            image = image_input

        # Detect
        boxes, _ = self.mtcnn.detect(image)
        
        faces = []
        if boxes is not None:
            for box in boxes:
                # box is [x1, y1, x2, y2]
                x1, y1, x2, y2 = [int(b) for b in box]
                
                # Add margin
                w = x2 - x1
                h = y2 - y1
                margin_x = int(w * 0.2)
                margin_y = int(h * 0.2)
                
                x1 = max(0, x1 - margin_x)
                y1 = max(0, y1 - margin_y)
                x2 = min(image.width, x2 + margin_x)
                y2 = min(image.height, y2 + margin_y)
                
                face = image.crop((x1, y1, x2, y2))
                faces.append(face)
        
        # If no faces found, return the whole image resized (fallback) logic could be handled by caller,
        # but here we just return empty list or maybe the center crop?
        # Let's return empty list if no faces, caller decides.
        return faces

    def process_video(self, video_path, num_frames=20):
        """
        Extracts frames from video, detects faces in them.
        Returns list of face images (PIL).
        """
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total_frames <= 0:
            total_frames = 300 # Fallback
            
        # Sample frames uniformly
        frame_indices = np.linspace(0, total_frames-1, num_frames, dtype=int)
        
        extracted_faces = []
        
        current_frame = 0
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            
            # Detect faces in this frame
            # Optimization: If we find a face in the first few frames, maybe track it? 
            # But simple detection per frame is robust.
            faces = self.detect_faces(pil_img)
            
            # Determine which face to pick? For now, pick the largest or all?
            # User requirement: "Average predictions"
            # It's better to collect ALL faces found in sampled frames.
            extracted_faces.extend(faces)
            
        cap.release()
        return extracted_faces
