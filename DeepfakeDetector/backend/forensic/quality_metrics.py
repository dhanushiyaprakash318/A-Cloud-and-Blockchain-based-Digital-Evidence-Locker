import cv2
import numpy as np

def check_image_quality(image_path_or_np):
    """
    Analyzes image quality to detect conditions that cause false positives:
    - Blur (Laplacian variance)
    - Low Light (Average brightness)
    - Over Exposure
    
    Returns: dict of metrics and flags.
    """
    if isinstance(image_path_or_np, str):
        img = cv2.imread(image_path_or_np)
        if img is None:
            # Try capturing first frame if it's a video or imread failed
            cap = cv2.VideoCapture(image_path_or_np)
            ret, frame = cap.read()
            cap.release()
            if ret:
                img = frame
            else:
                return {} # Return empty dict instead of None to avoid crashes
    else:
        # Assume numpy array RGB
        img = cv2.cvtColor(image_path_or_np, cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Blur Detection
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    is_blurry = laplacian_var < 100 # Threshold can be tuned
    
    # Brightness Detection
    avg_brightness = np.mean(gray)
    is_dark = avg_brightness < 40
    is_overexposed = avg_brightness > 220
    
    flags = []
    if is_blurry: flags.append("Blurry")
    if is_dark: flags.append("Low Light")
    if is_overexposed: flags.append("Overexposed")
    
    return {
        "blur_score": laplacian_var,
        "brightness": avg_brightness,
        "flags": flags,
        "quality_score": 1.0 - (0.2 * len(flags)) # Simple penalty
    }
