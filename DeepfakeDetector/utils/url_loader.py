import os
import requests
import yt_dlp
import re
from pathlib import Path
from utils.url_intelligence import URLIntelligence
from utils.url_security import URLSecurity

def download_from_url(url, save_dir="temp_downloads"):
    """
    Enhanced URL downloader with intelligence and security features.
    Downloads media from various URL types:
    - Direct links (jpg, png, mp4)
    - Shortened URLs (bit.ly, tinyurl)
    - GitHub raw links
    - Google Drive public links
    - Dropbox links
    - YouTube/Social media (via yt-dlp)
    - HTML pages with embedded media
    
    Returns: {
        'file_path': str or None,
        'url_info': dict,
        'security_info': dict,
        'error': str or None
    }
    """
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # Initialize intelligence modules
    url_intel = URLIntelligence()
    url_sec = URLSecurity()
    
    result = {
        'file_path': None,
        'url_info': {},
        'security_info': {},
        'error': None
    }
    
    try:
        # Step 1: Security Analysis
        security_info = url_sec.analyze_url(url)
        result['security_info'] = security_info
        
        # Warn if highly suspicious (but don't block - let user decide)
        if security_info['risk_level'] in ['high', 'critical']:
            print(f"⚠️ WARNING: Suspicious URL detected!")
            print(f"   Risk Level: {security_info['risk_level'].upper()}")
            print(f"   Risk Score: {security_info['risk_score']}/100")
            print(f"   Flags: {', '.join(security_info['flags'])}")
        
        # Step 2: Process URL with intelligence
        intel_result = url_intel.process_url(url, save_dir)
        result['url_info'] = intel_result.get('url_info', {})
        
        # Check if Google Drive (needs special handling)
        if intel_result.get('url_info', {}).get('requires_gdrive'):
            return _handle_google_drive(url, save_dir, result)
        
        # If intelligence module succeeded, return
        if intel_result['success']:
            result['file_path'] = intel_result['file_path']
            return result
        
        # Step 3: Fallback to yt-dlp for streaming/social media
        print("Trying yt-dlp for streaming content...")
        ydl_result = _download_with_ytdlp(url, save_dir)
        if ydl_result['success']:
            result['file_path'] = ydl_result['file_path']
            return result
        
        # All methods failed
        result['error'] = intel_result.get('error', 'Unknown error')
        return result
        
    except Exception as e:
        result['error'] = str(e)
        print(f"Download error: {e}")
        return result

def _handle_google_drive(url, save_dir, result):
    """Handle Google Drive downloads using gdown"""
    try:
        import gdown
        
        # Extract file ID
        file_id = None
        
        # Pattern 1: /d/{file_id}/
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
        
        # Pattern 2: id={file_id}
        if not file_id:
            match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
        
        # Pattern 3: Just the ID in the URL
        if not file_id:
            match = re.search(r'[-\w]{25,}', url)
            if match:
                file_id = match.group(0)
        
        if not file_id:
            result['error'] = "Could not extract Google Drive file ID"
            return result
        
        # Download using gdown
        save_path = os.path.join(save_dir, "downloaded_media")
        output = gdown.download(id=file_id, output=save_path, quiet=False)
        
        if output:
            result['file_path'] = output
            result['url_info']['source'] = 'Google Drive'
            return result
        else:
            result['error'] = "Google Drive download failed"
            return result
            
    except ImportError:
        result['error'] = "gdown not installed. Install with: pip install gdown"
        return result
    except Exception as e:
        result['error'] = f"Google Drive error: {e}"
        return result

def _download_with_ytdlp(url, save_dir):
    """Download using yt-dlp for streaming platforms"""
    result = {'success': False, 'file_path': None, 'error': None}
    
    ydl_opts = {
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
        'outtmpl': os.path.join(save_dir, 'downloaded_media.%(ext)s'),
        'quiet': True,
        'no_warnings': True,
        'socket_timeout': 30,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            downloaded_file = ydl.prepare_filename(info)
            
            if os.path.exists(downloaded_file):
                result['success'] = True
                result['file_path'] = downloaded_file
            else:
                result['error'] = "yt-dlp download completed but file not found"
                
    except Exception as e:
        result['error'] = f"yt-dlp error: {e}"
    
    return result

# Legacy function for backward compatibility
def download_from_url_simple(url, save_dir="temp_downloads"):
    """
    Simple version that returns just the file path (backward compatible)
    Returns: file_path (str) or None
    """
    result = download_from_url(url, save_dir)
    return result.get('file_path')

if __name__ == "__main__":
    # Test cases
    test_urls = [
        "https://raw.githubusercontent.com/pytorch/hub/master/images/dog.jpg",
        "https://bit.ly/3example",  # Example shortened URL
    ]
    
    for test_url in test_urls:
        print(f"\nTesting: {test_url}")
        result = download_from_url(test_url)
        if result['file_path']:
            print(f"✓ Downloaded to: {result['file_path']}")
        else:
            print(f"✗ Failed: {result['error']}")
