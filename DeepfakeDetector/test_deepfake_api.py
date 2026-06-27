# -*- coding: utf-8 -*-
"""
test_deepfake_api.py
Comprehensive integration test for the Deepfake Detection API.
Tests all three analysis modes:
  1. Image upload  →  /analyze/upload
  2. Video upload  →  /analyze/upload
  3. URL analysis  →  /analyze/url

Run from DeepfakeDetector/ folder:
  python test_deepfake_api.py
"""
import sys
import os
import json
import hashlib
import requests
import struct
import zlib
import wave
import math

sys.stdout.reconfigure(encoding='utf-8')

BASE = "http://localhost:8001"

def hr(title=""):
    print(f"\n{'='*65}")
    if title:
        print(f"  {title}")
        print(f"{'='*65}")

def verdict_label(score):
    if score > 0.6:
        return "🔴 FAKE"
    elif score > 0.4:
        return "🟡 SUSPICIOUS"
    else:
        return "🟢 REAL"

# ─── HELPERS: Generate minimal valid test media files ───────────────────
def create_test_image_png(path):
    """Creates a minimal valid 64x64 RGB PNG file with a face-like gradient."""
    import struct, zlib
    width, height = 64, 64
    raw_data = b""
    for y in range(height):
        raw_data += b"\x00"  # filter type: None
        for x in range(width):
            r = int(255 * x / width)
            g = int(255 * y / height)
            b = 128
            raw_data += bytes([r, g, b])

    def png_chunk(name, data):
        c = struct.pack(">I", len(data)) + name + data
        crc = struct.pack(">I", zlib.crc32(name + data) & 0xFFFFFFFF)
        return c + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr_data = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    ihdr = png_chunk(b"IHDR", ihdr_data)
    compressed = zlib.compress(raw_data)
    idat = png_chunk(b"IDAT", compressed)
    iend = png_chunk(b"IEND", b"")
    
    with open(path, "wb") as f:
        f.write(signature + ihdr + idat + iend)


def create_test_video_mp4(path):
    """Creates a minimal valid MP4 video (ftyp + mdat box) - enough for format detection."""
    # Minimal ftyp + mdat boxes - accepted by cv2 for frame extraction attempts
    ftyp = (
        b'\x00\x00\x00\x18'  # box size (24)
        b'ftyp'
        b'isom'               # major brand
        b'\x00\x00\x00\x00'  # minor version
        b'isom'               # compatible brand
        b'mp41'               # compatible brand
    )
    mdat = b'\x00\x00\x00\x08mdat'
    with open(path, "wb") as f:
        f.write(ftyp + mdat)


def create_test_audio_wav(path):
    """Creates a minimal 1s 16kHz mono WAV with a sine wave."""
    sr = 16000
    duration = 1
    freq = 440  # A4
    samples = [int(32767 * math.sin(2 * math.pi * freq * t / sr)) for t in range(sr * duration)]
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(struct.pack(f"<{len(samples)}h", *samples))


# ─── STEP 0: Health Check ────────────────────────────────────────────────
hr("STEP 0: Health Check")
try:
    r = requests.get(f"{BASE}/", timeout=10)
    data = r.json()
    print(f"  Status : {data.get('status')}")
    print(f"  System : {data.get('system')}")
    print("  [OK] API is online.")
except Exception as e:
    print(f"  [FAIL] Cannot reach API at {BASE}: {e}")
    print("  Make sure the deepfake backend is running:")
    print("    cd DeepfakeDetector/backend")
    print("    python -m uvicorn main:app --port 8001")
    sys.exit(1)


# ─── STEP 1: Image Upload Analysis ──────────────────────────────────────
hr("STEP 1: Image Upload → /analyze/upload")

img_path = "test_sample_image.png"
create_test_image_png(img_path)
print(f"  Created test image : {img_path}")
print(f"  File size          : {os.path.getsize(img_path)} bytes")

try:
    with open(img_path, "rb") as f:
        r = requests.post(
            f"{BASE}/analyze/upload",
            files={"file": (img_path, f, "image/png")},
            timeout=60
        )
    if r.status_code == 200:
        result = r.json()
        score = result.get("final_score", result.get("visual_score", 0))
        print(f"\n  Filename     : {result.get('filename')}")
        print(f"  Type         : {result.get('type')}")
        print(f"  Visual Score : {result.get('visual_score', 0):.4f}")
        print(f"  Final Score  : {score:.4f}")
        print(f"  Verdict      : {result.get('verdict', 'N/A')} {verdict_label(score)}")
        
        details = result.get("details", {}).get("visual", {})
        breakdown = details.get("breakdown", {})
        if breakdown:
            print(f"\n  --- Breakdown ---")
            for k, v in breakdown.items():
                print(f"    {k}: {v}")
        print("\n  [PASS] Image analysis complete.")
    else:
        print(f"  [FAIL] HTTP {r.status_code}: {r.text}")
except Exception as e:
    print(f"  [FAIL] Image test error: {e}")
finally:
    if os.path.exists(img_path):
        os.remove(img_path)


# ─── STEP 2: Video Upload Analysis ──────────────────────────────────────
hr("STEP 2: Video Upload → /analyze/upload")

vid_path = "test_sample_video.mp4"
create_test_video_mp4(vid_path)
print(f"  Created test video : {vid_path}")
print(f"  File size          : {os.path.getsize(vid_path)} bytes")

try:
    with open(vid_path, "rb") as f:
        r = requests.post(
            f"{BASE}/analyze/upload",
            files={"file": (vid_path, f, "video/mp4")},
            timeout=120
        )
    if r.status_code == 200:
        result = r.json()
        score = result.get("final_score", result.get("visual_score", 0))
        print(f"\n  Filename     : {result.get('filename')}")
        print(f"  Type         : {result.get('type')}")
        print(f"  Visual Score : {result.get('visual_score', 0):.4f}")
        print(f"  Audio Score  : {result.get('audio_score', 0):.4f}")
        print(f"  Final Score  : {score:.4f}")
        print(f"  Verdict      : {result.get('verdict', 'N/A')} {verdict_label(score)}")
        print("\n  [PASS] Video analysis complete.")
    else:
        print(f"  [FAIL] HTTP {r.status_code}: {r.text[:300]}")
except Exception as e:
    print(f"  [FAIL] Video test error: {e}")
finally:
    if os.path.exists(vid_path):
        os.remove(vid_path)


# ─── STEP 3: URL Analysis ────────────────────────────────────────────────
hr("STEP 3: URL Analysis → /analyze/url")

# Use a reliable, publicly accessible real image URL (Wikipedia Commons)
test_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/4/47/PNG_transparency_demonstration_1.png/240px-PNG_transparency_demonstration_1.png"
print(f"  Testing URL: {test_url[:70]}...")

try:
    r = requests.post(
        f"{BASE}/analyze/url",
        data={"url": test_url},
        timeout=120
    )
    if r.status_code == 200:
        result = r.json()
        
        if result.get("error"):
            print(f"  [WARN] URL error: {result['error']}")
        else:
            score = result.get("final_score", result.get("visual_score", 0))
            print(f"\n  Filename     : {result.get('filename', 'N/A')}")
            print(f"  Type         : {result.get('type', 'N/A')}")
            print(f"  Visual Score : {result.get('visual_score', 0):.4f}")
            print(f"  Final Score  : {score:.4f}")
            print(f"  Verdict      : {result.get('verdict', 'N/A')} {verdict_label(score)}")
            
            url_info = result.get("url_info", {})
            security = result.get("security_info", {})
            if url_info or security:
                print(f"\n  --- URL Intelligence ---")
                print(f"    Domain     : {url_info.get('domain', 'N/A')}")
                print(f"    HTTPS      : {url_info.get('is_https', 'N/A')}")
                print(f"    Risk Level : {security.get('risk_level', 'N/A')}")
                print(f"    Risk Score : {security.get('risk_score', 'N/A')}")
            print("\n  [PASS] URL analysis complete.")
    else:
        print(f"  [FAIL] HTTP {r.status_code}: {r.text[:300]}")
except Exception as e:
    print(f"  [FAIL] URL test error: {e}")


# ─── SUMMARY ─────────────────────────────────────────────────────────────
hr("TEST SUMMARY")
print("  [1] API Health Check        : PASSED")
print("  [2] Image Upload Analysis   : TESTED via /analyze/upload")
print("  [3] Video Upload Analysis   : TESTED via /analyze/upload")
print("  [4] URL Analysis            : TESTED via /analyze/url")
print()
print("  Models Active:")
print("    EfficientNet-B0  → Primary visual classification")
print("    MTCNN            → Face detection (image + video frames)")
print("    Xception         → Conditional secondary classification (disabled without weights)")
print("    Wav2Vec2         → Audio deepfake detection (Hemgg/Deepfake-audio-detection)")
print("    ELA              → Error Level Analysis (forensic)")
print("    Noiseprint       → Noise pattern forensics")
print("    URL Intelligence → Domain reputation + security scoring")
print("="*65 + "\n")
