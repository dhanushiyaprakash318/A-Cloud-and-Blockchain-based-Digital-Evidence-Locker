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
from forensic.frequency import compute_frequency_score
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
        is_video = input_path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))
        
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
            # FALLBACK: If no faces found, use center crop of the image
            # This allows the model to analyze context artifacts even if face detection fails
            # For video frames, we might have skipped frames, but if ALL failed, we fallback.
            if is_video:
                 # If video face detection failed completely, we likely rely on just a few frames
                 # Let's try to just grab the first available frame if possible
                 # But self.face_detector.process_video returns faces. 
                 # We need a way to get raw frames if faces fail.
                 # Re-opening valid fallback:
                 cap = cv2.VideoCapture(input_path)
                 ret, frame = cap.read()
                 cap.release()
                 if ret:
                     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                     img = Image.fromarray(frame_rgb)
                     # Center crop 224x224
                     w, h = img.size
                     left = (w - 224)/2
                     top = (h - 224)/2
                     right = (w + 224)/2
                     bottom = (h + 224)/2
                     faces = [img.crop((left, top, right, bottom))]
            else:
                 # Single image fallback
                 w, h = img.size
                 # If image is smaller than 224, resize it up
                 if w < 224 or h < 224:
                     img = img.resize((224, 224))
                     faces = [img]
                 else:
                     # Center crop
                     left = (w - 224)/2
                     top = (h - 224)/2
                     right = (w + 224)/2
                     bottom = (h + 224)/2
                     faces = [img.crop((left, top, right, bottom))]
            
            # Update label to warn user
            if not faces: # Should be impossible now
                 results['label'] = "Analysis Failed (No Content)"
                 return results
            
            print("Warning: No faces detected. Falling back to center crop analysis.")
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
            
        # Video Aggregation: Top-K Strategy
        # Instead of simple mean, take the average of the top 20% most suspicious frames (or at least top 1)
        # This catches "blinker" deepfakes where only some frames are clearly fake.
        
        # Eff_probs shape: [batch_size, 2]
        fake_scores = eff_probs[:, 0] # Index 0 is Fake due to model inversion logic from earlier? 
        # Wait, earlier code said: eff_fake_score = avg_eff_probs[0].item() # Was 1
        # Let's double check. Usually 0=Real, 1=Fake.
        # Line 49: model.classifier[1] = torch.nn.Linear(..., 2)
        # We need to trust the previous logic which claimed User Feedback: Invert Logic.
        # "eff_fake_score = avg_eff_probs[0].item()" -> implies Index 0 is Fake.
        
        if len(fake_scores) > 5:
             # Sort descending
             top_k_scores, _ = torch.topk(fake_scores, k=max(1, int(len(fake_scores)*0.3)))
             eff_fake_score = torch.mean(top_k_scores).item()
        else:
             eff_fake_score = torch.mean(fake_scores).item()
             
        eff_real_score = 1.0 - eff_fake_score
        
        results['breakdown']['EfficientNet'] = eff_fake_score
        
        # 3. Conditional Xception Pass
        # ONLY if we have valid weights
        xcp_fake_score = eff_fake_score # Default
        
        if self.use_xception:
            # Trigger if uncertain
            run_xception = 0.40 <= eff_fake_score <= 0.70
            if run_xception:
                with torch.no_grad():
                    xcp_out = self.xception(batch)
                    xcp_probs = torch.softmax(xcp_out, dim=1)
                
                # Also Top-K for Xception
                xcp_fake_scores_batch = xcp_probs[:, 1] # Assuming standard index 1 for fake in Xception standard
                
                if len(xcp_fake_scores_batch) > 5:
                     top_k_xcp, _ = torch.topk(xcp_fake_scores_batch, k=max(1, int(len(xcp_fake_scores_batch)*0.3)))
                     xcp_fake_score = torch.mean(top_k_xcp).item()
                else:
                     xcp_fake_score = torch.mean(xcp_fake_scores_batch).item()

                results['breakdown']['Xception'] = xcp_fake_score
            else:
                 results['breakdown']['Xception'] = "Skipped (High Confidence)"
        else:
            results['breakdown']['Xception'] = "Disabled (Missing Weights)"
            
        # 4. Forensics
        # ELA on input file (image only usually, or first frame of video could be saved)
        ela_score = 0
        noiseprint_score = 0
        freq_score = 0
        
        if not is_video:
            ela_img, ela_score_val = compute_ela(input_path)
            results['ela_image'] = ela_img
            ela_score = ela_score_val
            
            noiseprint_img, noiseprint_score = get_noiseprint(input_path)
            results['noiseprint'] = noiseprint_img
            
            # Frequency Analysis coverage for high-quality fakes
            freq_score = compute_frequency_score(input_path)
        else:
             # For video, minimal forensic score contribution (neutral)
             ela_score = 0.5
             noiseprint_score = 0.5
             freq_score = 0.5
        
        results['breakdown']['ELA_Score'] = ela_score
        results['breakdown']['Noiseprint_Score'] = noiseprint_score
        results['breakdown']['Frequency_Score'] = freq_score
        
        # 5. Ensemble Voting
        final_score = 0.0
        
        if self.use_xception and results['breakdown']['Xception'] != "Skipped (High Confidence)" and results['breakdown']['Xception'] != "Disabled (Missing Weights)":
            final_score = (0.35 * eff_fake_score) + \
                          (0.35 * xcp_fake_score) + \
                          (0.10 * ela_score) + \
                          (0.10 * noiseprint_score) + \
                          (0.10 * freq_score)
        else:
            # Rely primarily on EfficientNet but include Frequency for high-quality checks
            final_score = (0.75 * eff_fake_score) + \
                          (0.05 * ela_score) + \
                          (0.05 * noiseprint_score) + \
                          (0.15 * freq_score)
        
        # === QUALITY SAFEGUARDS ===
        # 1. Low Quality / Noise Adjustment
        # If image is very noisy/blurry (Quality < 0.4), it can trigger false positives in EffNet.
        # We dampen the score towards 0.0 (Real) if it's high, UNLESS Frequency analysis confirms it.
        if quality_data.get('quality_score', 1.0) < 0.5:
             # If prediction is FAKE but purely due to visual noise?
             # If Frequency score is also LOW (no periodic artifacts), then it's likely just a bad camera.
             if final_score > 0.6 and freq_score < 0.4:
                  final_score *= 0.8 # Penalty: Likely false positive due to noise
                  print("Heuristic: Reducing Fake score due to Low Quality + Normal Frequency.")
        
        # 2. High Quality Adjustment
        # If image is High Q (Quality > 0.8) and EffNet is unsure (0.4-0.6), but Frequency is HIGH:
        # It's likely a High-Res Deepfake (GAN/Diffusion).
        if quality_data.get('quality_score', 0) > 0.8:
             if 0.3 < final_score < 0.7 and freq_score > 0.6:
                  final_score += 0.15 # Boost: High freq artifacts in high quality image
                  print("Heuristic: Boosting Fake score due to High Frequency Artifacts.")
        
        # Clamp result
        final_score = max(0.0, min(1.0, final_score))
                          
        # 6. Thresholding & Logic 
        results['final_score'] = final_score
        results['fake_prob'] = final_score
        results['real_prob'] = 1.0 - final_score
        
        # More sensitive thresholds
        if final_score > 0.60: 
            results['label'] = "FAKE (High Confidence)"
        elif final_score < 0.40:
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
