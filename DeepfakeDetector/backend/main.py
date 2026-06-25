from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import shutil
import os
import uuid
import sys
import numpy as np

# Ensure we can import local modules (add parent dir)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from inference.predictor import HybridPredictor
from inference.audio_predictor import AudioForensics
from utils.url_loader import download_from_url
from utils.url_loader import download_from_url
from utils.report_generator import generate_report
import traceback

app = FastAPI(title="Deepfake Detective API", version="2.0")

# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Models (Lazy load or startup)
visual_model = HybridPredictor(device='cpu') # Loads EffNet
audio_model = AudioForensics()

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

@app.get("/")
def health_check():
    return {"status": "online", "system": "Deepfake Detective Hybrid Engine"}

def convert_numpy(obj):
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: convert_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy(i) for i in obj]
    return obj

@app.post("/analyze/upload")
async def analyze_upload(file: UploadFile = File(...)):
    try:
        # Save File
        ext = file.filename.split('.')[-1].lower()
        filename = f"{uuid.uuid4()}.{ext}"
        filepath = os.path.join(TEMP_DIR, filename)
        
        with open(filepath, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return await analyze_local_file(filepath, file.filename)

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

async def analyze_local_file(filepath, original_filename):
    # Determine Type
    ext = filepath.split('.')[-1].lower()
    is_video = ext in ['mp4', 'mov', 'avi', 'mkv', 'webm']
    is_audio = ext in ['wav', 'mp3', 'flac', 'm4a']
    
    response = {
        "filename": original_filename,
        "type": "video" if is_video else ("audio" if is_audio else "image"),
        "visual_score": 0,
        "audio_score": 0,
        "final_score": 0,
        "verdict": "Unknown",
        "details": {}
    }

    # --- PIPELINE ---
    
    # 1. Audio Analysis (if video or audio)
    audio_path = None
    if is_audio or is_video:
        # Extract audio from video if needed
        audio_path = filepath
        if is_video:
            try:
                from moviepy.editor import VideoFileClip
                # Check if file is valid video first
                clip = VideoFileClip(filepath)
                if clip.audio:
                    audio_path = filepath.replace(f".{ext}", ".wav")
                    clip.audio.write_audiofile(audio_path, logger=None)
                    clip.close()
                else:
                    audio_path = None
                    clip.close()
            except Exception as e:
                print(f"Audio extraction warning: {e}")
                audio_path = None

        if audio_path and os.path.exists(audio_path):
            try:
                a_res = audio_model.analyze(audio_path)
                response['audio_score'] = a_res['score']
                response['details']['audio'] = a_res
            except Exception as e:
                print(f"Audio analysis failed: {e}")
            finally:
                # Cleanup extracted audio if it was temp
                if is_video and audio_path and os.path.exists(audio_path):
                     os.remove(audio_path)
    
    # 2. Visual Analysis (if video or image)
    if not is_audio:
        try:
            v_res = visual_model.predict(filepath)
            response['visual_score'] = v_res['fake_prob']
            # Filter out heavy objects
            response['details']['visual'] = {k:v for k,v in v_res.items() if k not in ['heatmap', 'original_face', 'ela_image', 'noiseprint']}
        except Exception as e:
            print(f"Visual analysis failed: {e}")
            traceback.print_exc()

    # 3. Fusion
    if is_video and audio_path:
        # Max Evidence Fusion
        if response['visual_score'] > 0.7 or response['audio_score'] > 0.7:
            response['final_score'] = max(response['visual_score'], response['audio_score'])
        else:
                response['final_score'] = (0.6 * response['visual_score']) + (0.4 * response['audio_score'])
    elif is_audio:
        response['final_score'] = response['audio_score']
    else:
        response['final_score'] = response['visual_score']

    # Verdict
    score = response['final_score']
    if score > 0.6: response['verdict'] = "FAKE"
    elif score > 0.4: response['verdict'] = "SUSPICIOUS"
    else: response['verdict'] = "REAL"
    
    return convert_numpy(response)

@app.post("/analyze/url")
async def analyze_url_endpoint(url: str = Form(...)):
    # use utils.url_loader
    try:
        res = download_from_url(url, save_dir=TEMP_DIR)
        if res['error']:
            return {"error": res['error']}
            
        # Run analysis on downloaded file
        filepath = res['file_path']
        filename = os.path.basename(filepath)
        
        # Add URL info to response? 
        # For now just return the analysis
        analysis_result = await analyze_local_file(filepath, filename)
        
        # Inject URL info
        analysis_result['url_info'] = res.get('url_info', {})
        analysis_result['security_info'] = res.get('security_info', {})
        
        return analysis_result
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
