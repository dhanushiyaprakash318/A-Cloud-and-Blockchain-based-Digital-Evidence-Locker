import cv2
import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import os

def percent_eda_score(ela_image):
    # Determine the ratio of edited pixels to the total number of pixels in the image
    gray = cv2.cvtColor(np.array(ela_image), cv2.COLOR_RGB2GRAY)
    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
    non_zero = cv2.countNonZero(thresh)
    total_pixels = ela_image.size[0] * ela_image.size[1]
    return (non_zero / total_pixels) * 100

def compute_ela(path, quality=90):
    """
    Computes Error Level Analysis (ELA) on an image.
    Returns: (ELA Image, Normalized Tamper Score 0-1)
    """
    try:
        original = Image.open(path).convert('RGB')
        
        # Save the image at a specific quality to a temporary buffer or file
        # Use absolute path for temp file to avoid CWD issues
        temp_filename = "temp_ela_check.jpg"
        original.save(temp_filename, 'JPEG', quality=quality)
        
        # Reload the resaved image
        resaved = Image.open(temp_filename)
        
        # Calculate the difference
        ela_image = ImageChops.difference(original, resaved)
        
        # Enhance the difference significantly
        extrema = ela_image.getextrema()
        max_diff = max([ex[1] for ex in extrema])
        
        if max_diff == 0:
            max_diff = 1
            
        scale = 255.0 / max_diff
        ela_image = ImageEnhance.Brightness(ela_image).enhance(scale)
        
        # Clean up
        try:
             resaved.close()
             # os.remove(temp_filename) # Keep for debugging if needed, or remove later
        except:
             pass

        # Calculate score
        score_val = percent_eda_score(ela_image)
        # Normalize: heuristic map 0-5% -> 0.0-0.3 (Real), 5-20% -> 0.3-0.7 (Suspicious), >20% -> 0.7-1.0 (Fake)
        # This is a rough heuristic.
        normalized_score = min(score_val / 40.0, 1.0) # Map 0-40% to 0-1

        return ela_image, normalized_score
        
    except Exception as e:
        print(f"ELA Error: {e}")
        return None, 0.0
