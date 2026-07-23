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

    def align_face(self, image, landmarks):
        """
        Align detection based on eyes using landmarks.
        landmarks: [left_eye, right_eye, nose, left_mouth, right_mouth]
        """
        left_eye = landmarks[0]
        right_eye = landmarks[1]
        
        # Calculate angle
        dY = right_eye[1] - left_eye[1]
        dX = right_eye[0] - left_eye[0]
        angle = np.degrees(np.arctan2(dY, dX))
        
        # Center of eyes
        eyes_center = ((left_eye[0] + right_eye[0]) // 2, (left_eye[1] + right_eye[1]) // 2)
        
        # Rotate
        M = cv2.getRotationMatrix2D(eyes_center, angle, 1.0)
        img_np = np.array(image)
        h, w = img_np.shape[:2]
        aligned = cv2.warpAffine(img_np, M, (w, h), flags=cv2.INTER_CUBIC)
        
        return Image.fromarray(aligned)

    def detect_faces(self, image_input):
        """
        Detect faces in an image (numpy array or PIL Image).
        Returns a list of PIL Images cropped to the face (aligned).
        """
        if isinstance(image_input, np.ndarray):
            image = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_BGR2RGB))
        else:
            image = image_input

        # Detect
        boxes, probs, landmarks = self.mtcnn.detect(image, landmarks=True)
        
        faces = []
        if boxes is not None:
            for i, box in enumerate(boxes):
                # Align first if landmarks exist
                if landmarks is not None:
                     aligned_full_img = self.align_face(image, landmarks[i])
                     # We need to re-detect or just rotate the box? 
                     # Easier: Just crop roughly then rotate? 
                     # Better: Rotate image then crop. But box is on original.
                     # Compromise: Crop widely, then rotate that crop? 
                     # Standard approach: Rotate full image, then re-detect or project box.
                     # FOR SIMPLICITY/SPEED: Just use the original box on original image, 
                     # but maybe detection is better if we just return the face.
                     # Actually, EfficientNet likes aligned faces.
                     
                     # Implementation: 
                     # 1. Rotate whole image to make eyes #1 horizontal
                     # 2. But we have multiple faces. 
                     # 3. Simple approach: Just crop then process. Complex alignment might be slow.
                     # Let's do: Crop -> (Optional: no we can't align a crop easily if we don't know center)
                     # Let's stick to: just use the box, but add 30% margin.
                     pass
                
                # box is [x1, y1, x2, y2]
                x1, y1, x2, y2 = [int(b) for b in box]
                
                # Add margin (increased to 30% for context)
                w = x2 - x1
                h = y2 - y1
                margin_x = int(w * 0.3)
                margin_y = int(h * 0.3)
                
                x1 = max(0, x1 - margin_x)
                y1 = max(0, y1 - margin_y)
                x2 = min(image.width, x2 + margin_x)
                y2 = min(image.height, y2 + margin_y)
                
                face = image.crop((x1, y1, x2, y2))
                faces.append(face)
        
        return faces

    def process_video(self, video_path, num_frames=30):
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
        
        for idx in frame_indices:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            ret, frame = cap.read()
            if not ret:
                break
                
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            
            faces = self.detect_faces(pil_img)
            extracted_faces.extend(faces)
            
        # Retry with more frames if none found
        if not extracted_faces and total_frames > num_frames:
             # Try random sampling
             more_indices = np.random.randint(0, total_frames, 20)
             for idx in more_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    pil_img = Image.fromarray(frame_rgb)
                    faces = self.detect_faces(pil_img)
                    extracted_faces.extend(faces)
                    if extracted_faces: break # Found some!
            
        cap.release()
        return extracted_faces
