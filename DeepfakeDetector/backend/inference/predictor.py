import torch
import cv2
import numpy as np
from PIL import Image
from torchvision import transforms, models
import torch.nn.functional as F

from inference.face_detection import FaceDetector
from inference.xception_loader import XceptionDetector
from forensic.heatmap import GradCAM
from forensic.ela import compute_ela
from forensic.noiseprint import get_noiseprint
from forensic.quality_metrics import check_image_quality

class HybridPredictor:
    def __init__(self, model_path_eff='models/best_model-v3.pt', model_path_xcp=None, device='cpu'):
        self.device = device
        
        # === Load EfficientNet (Primary) ===
        self.effnet = self.load_effnet(model_path_eff)
        
        # === Load Xception (Secondary) ===
        # Pass None for model_path_xcp if we don't have one, it will init with ImageNet (suboptimal but runs)
        # Ideally user provides weights.
        self.use_xception = False
        self.xception = XceptionDetector(pretrained=True, device=device)
        if model_path_xcp:
            self.xception.load_weights(model_path_xcp)
            self.use_xception = True
        else:
            print("Warning: No custom Xception weights provided. Disabling Xception voting to avoid random noise.")
            
        self.face_detector = FaceDetector(device=device)
        
        # Common Preprocessing
        self.preprocess = transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225])
        ])
        
        # GradCAM for EffNet
        target_layer = self.effnet.features[-1]
        self.grad_cam = GradCAM(self.effnet, target_layer)

    def load_effnet(self, path):
        model = models.efficientnet_b0(weights=None)
        model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, 2)
        try:
            state_dict = torch.load(path, map_location=self.device)
            model.load_state_dict(state_dict)
        except Exception as e:
            print(f"Error loading EffNet: {e}")
        model.to(self.device)
        model.eval()
        return model

    def predict(self, input_path):
        is_video = input_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv'))
        
        # Quality Check
        quality_data = check_image_quality(input_path)   
        
        # Init results
        results = {
            'type': 'video' if is_video else 'image',
            'faces_found': 0,
            'real_prob': 0.0,
            'fake_prob': 0.0,
            'label': 'Unknown',
            'heatmap': None,
            'original_face': None,
            'ela_image': None,
            'noiseprint': None,
            'quality': quality_data,
            'breakdown': {}
        }

        # 1. Face Detect
        if is_video:
            faces = self.face_detector.process_video(input_path, num_frames=30) # Increased frames
        else:
            img = Image.open(input_path).convert('RGB')
            faces = self.face_detector.detect_faces(img)
            if not faces: faces = [img]

        if not faces:
            results['label'] = "No Faces Found"
            return results
            
        results['faces_found'] = len(faces)
        
        # Batch preparation
        batch_tensors = []
        for face in faces:
            batch_tensors.append(self.preprocess(face))
            
        if not batch_tensors:
            return results
            
        batch = torch.stack(batch_tensors).to(self.device)
        
        # 2. EfficientNet Pass
        with torch.no_grad():
            full_out = self.effnet(batch)
            eff_probs = torch.softmax(full_out, dim=1)
            
        avg_eff_probs = torch.mean(eff_probs, dim=0)
        eff_fake_score = avg_eff_probs[1].item()
        eff_real_score = avg_eff_probs[0].item()
        
        results['breakdown']['EfficientNet'] = eff_fake_score
        
        # 3. Conditional Xception Pass
        # Trigger if EffNet is uncertain (e.g., between 0.4 and 0.7) OR if suspicious
        xcp_fake_score = eff_fake_score # Default if skipped
        
        run_xception = 0.40 <= eff_fake_score <= 0.70
        
        if run_xception:
            with torch.no_grad():
                xcp_out = self.xception(batch)
                xcp_probs = torch.softmax(xcp_out, dim=1)
            avg_xcp_probs = torch.mean(xcp_probs, dim=0)
            xcp_fake_score = avg_xcp_probs[1].item()
            results['breakdown']['Xception'] = xcp_fake_score
        else:
            results['breakdown']['Xception'] = "Skipped (High Confidence)"
            
        # 4. Forensics
        # ELA on input file (image only usually, or first frame of video could be saved)
        ela_score = 0
        noiseprint_score = 0
        if not is_video:
            ela_img, ela_score_val = compute_ela(input_path)
            results['ela_image'] = ela_img
            ela_score = ela_score_val
            
            noiseprint_img, noiseprint_score = get_noiseprint(input_path)
            results['noiseprint'] = noiseprint_img
        else:
             # For video, minimal forensic score contribution (neutral)
             ela_score = 0.5
             noiseprint_score = 0.5
        
        results['breakdown']['ELA_Score'] = ela_score
        results['breakdown']['Noiseprint_Score'] = noiseprint_score
        
        # 5. Ensemble Voting
        # NEW WEIGHTS: 0.35 EffNet + 0.45 Xception + 0.10 ELA + 0.10 Noiseprint
        
        final_score = 0.0
        
        if self.use_xception and run_xception:
            final_score = (0.35 * eff_fake_score) + \
                          (0.45 * xcp_fake_score) + \
                          (0.10 * ela_score) + \
                          (0.10 * noiseprint_score)
        else:
            # Xception disabled or skipped - adjust weights
            # Rely more on EffNet and forensics
            final_score = (0.70 * eff_fake_score) + \
                          (0.15 * ela_score) + \
                          (0.15 * noiseprint_score)
        
        # === FALSE POSITIVE REDUCTION HEURISTICS ===
        # 1. ELA Bonus: If ELA is very low (consistent), it's likely Real.
        if ela_score < 0.15:
            final_score -= 0.15 # Strong bonus for looking consistent
            
        # 2. Quality Penalty: If poor quality, reduce confidence in "Fake" prediction
        if quality_data and quality_data['quality_score'] < 0.6:
             final_score *= 0.8
        
        # Clamp result
        final_score = max(0.0, min(1.0, final_score))
                          
        # 6. Thresholding & Logic 
            
        results['final_score'] = final_score
        results['fake_prob'] = final_score
        results['real_prob'] = 1.0 - final_score
        
        if final_score > 0.85:
            results['label'] = "FAKE (High Confidence)"
        elif final_score < 0.25:
            results['label'] = "REAL (High Confidence)"
        else:
            results['label'] = "SUSPICIOUS (Needs Review)"
            
        # Visuals (GradCAM on EffNet)
        # Find index of face with highest fake prob in EffNet batch
        target_idx = torch.argmax(eff_probs[:, 1]).item()
        
        cam, _ = self.grad_cam(batch[target_idx].unsqueeze(0))
        heatmap_img = cv2.applyColorMap(np.uint8(255 * cam), cv2.COLORMAP_JET)
        heatmap_img = cv2.cvtColor(heatmap_img, cv2.COLOR_BGR2RGB)
        target_face_img = faces[target_idx]
        heatmap_img = cv2.resize(heatmap_img, target_face_img.size)
        face_np = np.array(target_face_img)
        overlay = cv2.addWeighted(face_np, 0.6, heatmap_img, 0.4, 0)
        
        results['heatmap'] = Image.fromarray(overlay)
        results['original_face'] = target_face_img
        
        return results
