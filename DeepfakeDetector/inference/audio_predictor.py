import torch
import librosa
import numpy as np
from transformers import Wav2Vec2ForSequenceClassification, Wav2Vec2FeatureExtractor

class AudioForensics:
    def __init__(self, model_name="Hemgg/Deepfake-audio-detection", device=None):
        self.device = device if device else ("cuda" if torch.cuda.is_available() else "cpu")
        print(f"Loading Audio Deepfake Model: {model_name} on {self.device}...")
        
        try:
            self.feature_extractor = Wav2Vec2FeatureExtractor.from_pretrained(model_name)
            self.model = Wav2Vec2ForSequenceClassification.from_pretrained(model_name)
            self.model.to(self.device)
            self.model.eval()
            self.model_loaded = True
        except Exception as e:
            print(f"Failed to load Audio Model: {e}")
            self.model_loaded = False
        
    def analyze(self, audio_path):
        return self.predict(audio_path)

    def predict(self, audio_path):
        if not self.model_loaded:
             return {"score": 0.0, "label": "ERROR", "details": "Model not loaded"}

        try:
            # Load audio
            # Wav2Vec2 expects 16kHz
            speech, sr = librosa.load(audio_path, sr=16000)
            
            # Preprocess
            inputs = self.feature_extractor(speech, sampling_rate=16000, return_tensors="pt", padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Inference
            with torch.no_grad():
                logits = self.model(**inputs).logits
                
            probs = torch.softmax(logits, dim=-1)
            fake_prob = probs[0][1].item() # Assuming index 1 is fake
            real_prob = probs[0][0].item() # Assuming index 0 is real
            
            label = "FAKE" if fake_prob > 0.5 else "REAL"
            
            # Detailed stats (optional, mimicking the image predictor structure)
            return {
                "score": fake_prob, # Main.py expects 'score'
                "label": label,
                "fake_prob": fake_prob,
                "real_prob": real_prob,
                "confidence": max(fake_prob, real_prob),
                "breakdown": {
                    "DeepLearning_Score": fake_prob,
                    "Model": "Wav2Vec2-Base"
                }
            }
        except Exception as e:
            print(f"Audio Prediction Error: {e}")
            return {"score": 0.0, "label": "ERROR", "fake_prob": 0, "real_prob": 0, "error": str(e)}

if __name__ == "__main__":
    # Simple test
    predictor = AudioPredictor()
    print("Model initialized successfully.")
