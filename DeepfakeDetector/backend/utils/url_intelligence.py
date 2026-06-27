"""
URL Intelligence Module
Handles smart URL processing, redirect resolution, content detection, and media extraction
"""

import os
import re
import requests
from urllib.parse import urlparse, urljoin, parse_qs
from typing import Dict, List, Optional, Tuple
import time
from pathlib import Path

class URLIntelligence:
    """Smart URL handler for processing any URL type"""
    
    def __init__(self, timeout=30, max_redirects=10):
        self.timeout = timeout
        self.max_redirects = max_redirects
        self.session = requests.Session()
        
        # Set realistic headers to avoid 403 errors
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        
    def resolve_redirects(self, url: str) -> Dict:
        """
        Follow redirects and return the final URL with chain information
        Returns: {
            'final_url': str,
            'redirect_chain': List[str],
            'redirect_count': int,
            'is_suspicious': bool
        }
        """
        redirect_chain = [url]
        current_url = url
        
        try:
            for i in range(self.max_redirects):
                response = self.session.head(current_url, allow_redirects=False, timeout=self.timeout)
                
                # Check if it's a redirect
                if response.status_code in [301, 302, 303, 307, 308]:
                    next_url = response.headers.get('Location')
                    if not next_url:
                        break
                    
                    # Handle relative URLs
                    if not next_url.startswith('http'):
                        next_url = urljoin(current_url, next_url)
                    
                    redirect_chain.append(next_url)
                    current_url = next_url
                else:
                    break
            
            # Check for suspicious redirect patterns
            is_suspicious = len(redirect_chain) > 5 or self._has_cross_domain_redirects(redirect_chain)
            
            return {
                'final_url': current_url,
                'redirect_chain': redirect_chain,
                'redirect_count': len(redirect_chain) - 1,
                'is_suspicious': is_suspicious
            }
            
        except Exception as e:
            print(f"Redirect resolution error: {e}")
            return {
                'final_url': url,
                'redirect_chain': [url],
                'redirect_count': 0,
                'is_suspicious': False
            }
    
    def _has_cross_domain_redirects(self, chain: List[str]) -> bool:
        """Check if redirect chain crosses multiple domains suspiciously"""
        domains = [urlparse(url).netloc for url in chain]
        unique_domains = set(domains)
        return len(unique_domains) > 3  # More than 3 different domains is suspicious
    
    def detect_content_type(self, url: str) -> Dict:
        """
        Detect the content type of the URL
        Returns: {
            'content_type': str,  # 'image', 'video', 'html', 'stream', 'unknown'
            'mime_type': str,
            'is_direct_media': bool
        }
        """
        try:
            # First check URL extension
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Direct media extensions
            image_exts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            video_exts = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
            
            is_direct_media = False
            content_type = 'unknown'
            
            if any(path.endswith(ext) for ext in image_exts):
                content_type = 'image'
                is_direct_media = True
            elif any(path.endswith(ext) for ext in video_exts):
                content_type = 'video'
                is_direct_media = True
            
            # If not obvious from extension, check Content-Type header
            try:
                response = self.session.head(url, allow_redirects=True, timeout=self.timeout)
                response.raise_for_status()
            except Exception:
                try:
                    response = self.session.get(url, allow_redirects=True, timeout=self.timeout, stream=True)
                    response.raise_for_status()
                except Exception as e:
                    print(f"Content type detection warning: HEAD+GET failed: {e}")
                    return {
                        'content_type': content_type,
                        'mime_type': 'unknown',
                        'is_direct_media': is_direct_media
                    }

            mime_type = response.headers.get('Content-Type', '').lower()

            if 'image' in mime_type:
                content_type = 'image'
                is_direct_media = True
            elif 'video' in mime_type:
                content_type = 'video'
                is_direct_media = True
            elif 'text/html' in mime_type:
                content_type = 'html'
            elif 'application/octet-stream' in mime_type:
                content_type = 'stream'

            return {
                'content_type': content_type,
                'mime_type': mime_type,
                'is_direct_media': is_direct_media
            }
            return {
                'content_type': 'unknown',
                'mime_type': 'unknown',
                'is_direct_media': False
            }
    
    def extract_media_from_html(self, url: str, html_content: str = None) -> List[str]:
        """
        Extract media URLs from HTML page
        Returns list of media URLs found
        """
        try:
            from bs4 import BeautifulSoup
            
            # Fetch HTML if not provided
            if html_content is None:
                response = self.session.get(url, timeout=self.timeout)
                html_content = response.text
            
            soup = BeautifulSoup(html_content, 'html.parser')
            media_urls = []
            
            # 1. Check Open Graph meta tags (most reliable for social media)
            og_video = soup.find('meta', property='og:video')
            og_video_secure = soup.find('meta', property='og:video:secure_url')
            og_image = soup.find('meta', property='og:image')
            
            if og_video:
                media_urls.append(og_video.get('content'))
            if og_video_secure:
                media_urls.append(og_video_secure.get('content'))
            if og_image:
                media_urls.append(og_image.get('content'))
            
            # 2. Check Twitter meta tags
            twitter_player = soup.find('meta', attrs={'name': 'twitter:player:stream'})
            twitter_image = soup.find('meta', attrs={'name': 'twitter:image'})
            
            if twitter_player:
                media_urls.append(twitter_player.get('content'))
            if twitter_image:
                media_urls.append(twitter_image.get('content'))
            
            # 3. Find <video> tags
            for video in soup.find_all('video'):
                src = video.get('src')
                if src:
                    media_urls.append(src)
                
                # Check <source> tags inside <video>
                for source in video.find_all('source'):
                    src = source.get('src')
                    if src:
                        media_urls.append(src)
            
            # 4. Find <img> tags (only if no video found)
            if not media_urls:
                for img in soup.find_all('img'):
                    src = img.get('src')
                    if src and not src.startswith('data:'):  # Skip base64 images
                        # Filter out small icons/logos
                        width = img.get('width', 0)
                        height = img.get('height', 0)
                        try:
                            if width and height:
                                if int(width) > 200 and int(height) > 200:
                                    media_urls.append(src)
                            else:
                                media_urls.append(src)
                        except:
                            media_urls.append(src)
            
            # Convert relative URLs to absolute
            absolute_urls = []
            for media_url in media_urls:
                if media_url.startswith('http'):
                    absolute_urls.append(media_url)
                else:
                    absolute_urls.append(urljoin(url, media_url))
            
            # Remove duplicates while preserving order
            seen = set()
            unique_urls = []
            for u in absolute_urls:
                if u not in seen:
                    seen.add(u)
                    unique_urls.append(u)
            
            return unique_urls
            
        except Exception as e:
            print(f"HTML media extraction error: {e}")
            return []
    
    def handle_special_urls(self, url: str) -> Optional[str]:
        """
        Handle special URL types (GitHub, Google Drive, Dropbox)
        Returns modified URL or None if no special handling needed
        """
        
        # 1. GitHub blob URLs -> raw URLs
        if 'github.com' in url and '/blob/' in url:
            modified_url = url.replace('github.com', 'raw.githubusercontent.com').replace('/blob/', '/')
            print(f"GitHub URL converted: {modified_url}")
            return modified_url
        
        # 2. Dropbox URLs
        if 'dropbox.com' in url:
            # Change dl=0 to dl=1 for direct download
            if 'dl=0' in url:
                modified_url = url.replace('dl=0', 'dl=1')
                print(f"Dropbox URL converted: {modified_url}")
                return modified_url
            elif '?' not in url:
                modified_url = url + '?dl=1'
                print(f"Dropbox URL converted: {modified_url}")
                return modified_url
        
        # 3. Google Drive URLs - return special marker
        if 'drive.google.com' in url:
            return 'GDRIVE:' + url  # Special marker for Google Drive
        
        return None
    
    def download_direct_media(self, url: str, save_path: str, progress_callback=None) -> bool:
        """
        Download direct media file with progress tracking
        Returns True if successful
        """
        try:
            response = self.session.get(url, stream=True, timeout=self.timeout)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback and total_size > 0:
                            progress = (downloaded / total_size) * 100
                            progress_callback(progress)
            
            return True
            
        except Exception as e:
            print(f"Direct download error: {e}")
            return False
    
    def process_url(self, url: str, save_dir: str = "temp_downloads") -> Dict:
        """
        Main URL processing pipeline
        Returns: {
            'success': bool,
            'file_path': str,
            'url_info': dict,
            'security_info': dict,
            'error': str
        }
        """
        result = {
            'success': False,
            'file_path': None,
            'url_info': {},
            'security_info': {},
            'error': None
        }
        
        try:
            # Create save directory
            os.makedirs(save_dir, exist_ok=True)
            
            # Step 1: Handle special URLs
            special_url = self.handle_special_urls(url)
            if special_url:
                if special_url.startswith('GDRIVE:'):
                    # Google Drive needs special handling (will be done by caller)
                    result['url_info']['requires_gdrive'] = True
                    result['url_info']['original_url'] = url
                    return result
                else:
                    url = special_url
            
            # Step 2: Resolve redirects
            redirect_info = self.resolve_redirects(url)
            result['url_info']['redirect_info'] = redirect_info
            final_url = redirect_info['final_url']
            
            # Step 3: Detect content type
            content_info = self.detect_content_type(final_url)
            result['url_info']['content_info'] = content_info
            
            # Step 4: Process based on content type
            if content_info['is_direct_media']:
                # Direct download
                ext = Path(urlparse(final_url).path).suffix or '.mp4'
                save_path = os.path.join(save_dir, f"downloaded_media{ext}")
                
                if self.download_direct_media(final_url, save_path):
                    result['success'] = True
                    result['file_path'] = save_path
                else:
                    result['error'] = "Failed to download direct media"
                    
            elif content_info['content_type'] == 'html':
                # Extract media from HTML
                media_urls = self.extract_media_from_html(final_url)
                result['url_info']['extracted_media'] = media_urls
                
                if media_urls:
                    # Try to download the first media URL
                    first_media = media_urls[0]
                    ext = Path(urlparse(first_media).path).suffix or '.mp4'
                    save_path = os.path.join(save_dir, f"downloaded_media{ext}")
                    
                    if self.download_direct_media(first_media, save_path):
                        result['success'] = True
                        result['file_path'] = save_path
                    else:
                        result['error'] = "Failed to download extracted media"
                else:
                    result['error'] = "No media found in HTML page"
            else:
                result['error'] = f"Unsupported content type: {content_info['content_type']}"
            
            return result
            
        except Exception as e:
            result['error'] = str(e)
            return result
