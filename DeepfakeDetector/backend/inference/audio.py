import os
import numpy as np
import librosa
import traceback

class AudioForensics:
    def __init__(self):
        print("Initialized AudioForensics (CPU-Optimized)")

    def extract_features(self, y, sr):
        # 1. Spectral Flatness
        flatness = librosa.feature.spectral_flatness(y=y)
        feat_flatness = np.mean(flatness)

        # 2. Zero Crossing Rate
        zcr = librosa.feature.zero_crossing_rate(y)
        feat_zcr_std = np.std(zcr)

        # 3. MFCC Variance
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=13)
        feat_mfcc_var = np.mean(np.var(mfccs, axis=1))

        # 4. Spectral Centroid
        cent = librosa.feature.spectral_centroid(y=y, sr=sr)
        feat_cent_std = np.std(cent)
        
        # 5. Silence Ratio
        energy = librosa.feature.rms(y=y)
        silence_ratio = np.sum(energy < 0.01) / len(energy[0])

        return {
            "flatness": feat_flatness,
            "zcr_var": feat_zcr_std,
            "mfcc_var": feat_mfcc_var,
            "centroid_var": feat_cent_std,
            "silence_ratio": silence_ratio
        }

    def analyze(self, audio_path):
        try:
            # Load Audio (max 20s)
            y, sr = librosa.load(audio_path, sr=16000, duration=20.0)
            
            if np.max(np.abs(y)) < 0.005:
                return {
                    "is_fake": False,
                    "confidence": 1.0, 
                    "label": "Silence",
                    "score": 0.0
                }

            features = self.extract_features(y, sr)
            
            # === FORENSIC LOGIC ===
            score = 0.0
            anomalies = []
            
            # Checks
            if features['flatness'] > 0.015:
                score += 0.30
                anomalies.append("High Spectral Flatness (Robotic)")
            elif features['flatness'] < 0.0005:
                score += 0.15
                anomalies.append("Unnaturally Clean")
                
            if features['zcr_var'] < 0.01:
                score += 0.25
                anomalies.append("Low Pitch Variability (Monotone)")
                
            if features['mfcc_var'] < 20.0:
                 score += 0.30
                 anomalies.append("Synthetic Timbre")
                 
            # Result
            final_score = min(0.95, score)
            
            label = "REAL"
            if final_score > 0.5: label = "FAKE"
            
            return {
                "score": final_score,
                "label": label,
                "anomalies": anomalies,
                "features": features
            }

        except Exception as e:
            print(f"Audio Analysis Error: {e}")
            return {"score": 0, "label": "Error", "error": str(e)}
