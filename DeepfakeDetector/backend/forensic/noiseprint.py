import cv2
import numpy as np
from PIL import Image

def get_noiseprint(image_path):
    """
    Extracts high-frequency noise from the image (Noiseprint approximation).
    Uses a high-pass filter.
    Returns: (noiseprint_image, noiseprint_score)
    """
    img = cv2.imread(image_path)
    if img is None:
        return None, 0.0
    
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Simple high-pass filter kernel
    kernel = np.array([[-1, -1, -1],
                       [-1,  8, -1],
                       [-1, -1, -1]])
    
    high_pass = cv2.filter2D(gray, -1, kernel)
    
    # Calculate score: higher variance in noise = more suspicious
    noise_variance = np.var(high_pass)
    # Normalize to 0-1 range (heuristic: variance > 1000 is suspicious)
    noiseprint_score = min(noise_variance / 2000.0, 1.0)
    
    # Normalize for visualization
    high_pass = cv2.normalize(high_pass, None, 0, 255, cv2.NORM_MINMAX)
    
    return Image.fromarray(high_pass.astype(np.uint8)), noiseprint_score
