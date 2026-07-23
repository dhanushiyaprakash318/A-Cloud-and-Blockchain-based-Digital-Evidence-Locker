import sys
import os

# Add root to path
sys.path.append(os.getcwd())

try:
    print("Testing Imports...")
    from inference.predictor import HybridPredictor
    from inference.audio_predictor import AudioForensics
    from inference.face_detection import FaceDetector
    print("Imports Successful.")

    print("Initializing AudioForensics...")
    # Mocking model init to avoid downloading if possible, or just let it fail gracefully if model not found
    try:
        audio = AudioForensics(device='cpu')
        print("AudioForensics Initialized.")
    except Exception as e:
        print(f"AudioForensics Init Warning (expected if model missing): {e}")

    print("Initializing FaceDetector...")
    fd = FaceDetector(device='cpu')
    print("FaceDetector Initialized.")

    print("Initializing HybridPredictor...")
    # This might try to load 'models/best_model-v3.pt'
    if os.path.exists('models/best_model-v3.pt'):
        predictor = HybridPredictor(device='cpu')
        print("HybridPredictor Initialized.")
    else:
        print("Skipping HybridPredictor init (model not found).")

    print("\nVERIFICATION PASSED: No syntax errors in modified files.")

except Exception as e:
    print(f"\nVERIFICATION FAILED: {e}")
    import traceback
    traceback.print_exc()
