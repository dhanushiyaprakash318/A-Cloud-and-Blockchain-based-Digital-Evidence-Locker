import ssl
import socket
from pathlib import Path
from typing import Dict
from urllib.parse import urlparse

import requests
import validators

from config import WEBSITE_TIMEOUT
from utils.website_risk import analyze_url_safety, classify_website, risk_score_from_analysis


class WebsiteRiskDetector:
    def __init__(self):
        self.timeout = WEBSITE_TIMEOUT
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def _validate_website_url(self, url: str) -> None:
        if not validators.url(url):
            raise ValueError('Invalid URL format.')

        parsed = urlparse(url)
        if parsed.scheme.lower() not in {'http', 'https'}:
            raise ValueError('URL must use http or https.')

        extension = Path(parsed.path).suffix.lower()
        if extension:
            raise ValueError('URL must be a website address, not a direct media link.')

    def _is_direct_media_url(self, url: str) -> bool:
        try:
            response = requests.head(url, timeout=self.timeout, headers=self.headers, allow_redirects=True)
            content_type = response.headers.get('Content-Type', '').lower()
            return 'image' in content_type or 'video' in content_type
        except Exception:
            return False

    def analyze_website(self, url: str) -> Dict[str, object]:
        self._validate_website_url(url)

        if self._is_direct_media_url(url):
            raise ValueError('URL appears to be a direct media asset. Please submit a website URL.')

        analysis = analyze_url_safety(url)
        classification, confidence, reason = classify_website(analysis)
        risk_score = risk_score_from_analysis(analysis)

        return {
            'classification': classification,
            'confidence': confidence,
            'risk_score': risk_score,
            'reason': reason,
            'hostname': analysis.get('hostname'),
            'is_https': analysis.get('is_https', False),
        }
