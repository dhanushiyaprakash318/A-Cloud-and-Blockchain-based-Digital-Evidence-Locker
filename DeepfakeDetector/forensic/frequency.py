import cv2
import numpy as np

def compute_frequency_score(image_path_or_input):
    """
    Computes a score based on frequency domain anomalies.
    Deepfakes often have artifacts in the high-frequency spectrum.
    
    Returns:
        float: score between 0.0 (Real/Normal) and 1.0 (Fake/Anomalous)
    """
    try:
        # Load image
        if isinstance(image_path_or_input, str):
            img = cv2.imread(image_path_or_input, cv2.IMREAD_GRAYSCALE)
        else:
            # Assume PIL or numpy, convert to numpy grayscale
            img = np.array(image_path_or_input)
            if len(img.shape) == 3:
                img = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
                
        if img is None:
            return 0.5
            
        # Resize to standard size (e.g., 512x512) for consistency
        img = cv2.resize(img, (512, 512))
        
        # FFT
        f = np.fft.fft2(img)
        fshift = np.fft.fftshift(f)
        magnitude_spectrum = 20 * np.log(np.abs(fshift) + 1e-8)
        
        # Azimuthal Average calculation (simplified)
        # We look for "bumps" or lack of natural 1/f falloff
        
        # For this simplified version, we'll check the ratio of high-freq energy vs low-freq
        h, w = magnitude_spectrum.shape
        center_y, center_x = h // 2, w // 2
        
        # Low freq: circle in middle. High freq: outside.
        y, x = np.ogrid[:h, :w]
        dist_from_center = np.sqrt((x - center_x)**2 + (y - center_y)**2)
        
        low_freq_mask = dist_from_center <= 30
        high_freq_mask = dist_from_center > 60
        
        low_energy = np.mean(magnitude_spectrum[low_freq_mask])
        high_energy = np.mean(magnitude_spectrum[high_freq_mask])
        
        # Real images usually have specific falloff. Deepfakes (GANs) often have "checkerboard" high freq spikes.
        # This is a heuristic: if high freq energy is unusually high relative to low freq
        ratio = high_energy / (low_energy + 1e-6)
        
        # Normalize score (heuristic mapping)
        # Typical real image ratio ~ 0.3 - 0.5 depending on texture
        # Spikes might push it up or weirdly down.
        # Let's use a variance check on the high freq
        high_freq_var = np.var(magnitude_spectrum[high_freq_mask])
        
        # Heuristic: Fakes often have weird high-freq variance patterns
        score = 0.0
        if high_freq_var > 50: # Arbitrary threshold for "noisy/artifacty" spectrum
             score = 0.6
        else:
             score = 0.2
             
        # Just a placeholder for now - a real implementation needs the azimuthal integration 1D profile
        return score
        
    except Exception as e:
        print(f"Frequency Analysis Error: {e}")
        return 0.0
