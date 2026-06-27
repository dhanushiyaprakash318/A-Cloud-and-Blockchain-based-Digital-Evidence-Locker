import ssl
import socket
import re
from typing import Dict, Optional, Tuple
from urllib.parse import urlparse

import requests
from requests.exceptions import SSLError, RequestException

from config import (
    WEBSITE_TIMEOUT,
    SUSPICIOUS_DOMAIN_KEYWORDS,
    SUSPICIOUS_PATH_KEYWORDS,
    SECURITY_HEADERS,
)


def normalize_domain(hostname: str) -> str:
    return hostname.lower().strip()


def resolve_dns(hostname: str) -> Tuple[bool, Optional[str]]:
    try:
        answers = socket.getaddrinfo(hostname, None)
        ips = {item[4][0] for item in answers}
        return True, ', '.join(sorted(ips))
    except Exception:
        return False, None


def validate_ssl(hostname: str) -> Tuple[bool, Optional[str]]:
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=WEBSITE_TIMEOUT) as sock:
            with context.wrap_socket(sock, server_hostname=hostname):
                return True, 'Valid SSL certificate'
    except Exception as exc:
        return False, str(exc)


def analyze_security_headers(headers: Dict[str, str]) -> Tuple[int, list[str]]:
    score = 0
    reasons = []
    lower_headers = {k.lower(): v for k, v in headers.items()}

    for header in SECURITY_HEADERS:
        if header in lower_headers:
            score += 1
        else:
            reasons.append(f'Missing {header}')

    return score, reasons


def detect_typosquatting(hostname: str) -> Tuple[bool, Optional[str]]:
    cleaned = normalize_domain(hostname)
    if any(token in cleaned for token in SUSPICIOUS_DOMAIN_KEYWORDS):
        return True, 'Suspicious domain keywords present'

    if cleaned.count('-') >= 2 or cleaned.count('.') >= 3:
        return True, 'Unusual domain formatting'

    return False, None


def analyze_url_safety(url: str) -> Dict[str, object]:
    parsed = urlparse(url)
    hostname = parsed.hostname or ''
    path = parsed.path or ''
    normalized_hostname = normalize_domain(hostname)

    is_https = parsed.scheme.lower() == 'https'
    ssl_valid, ssl_reason = validate_ssl(hostname) if is_https else (False, 'URL is not HTTPS')
    dns_resolved, dns_info = resolve_dns(hostname)
    typosquatting, typosquatting_reason = detect_typosquatting(hostname)
    analysis = {
        'hostname': hostname,
        'is_https': is_https,
        'ssl_valid': ssl_valid,
        'ssl_reason': ssl_reason,
        'dns_resolved': dns_resolved,
        'dns_info': dns_info,
        'typosquatting': typosquatting,
        'typosquatting_reason': typosquatting_reason,
        'security_header_score': 0,
        'security_header_reasons': [],
        'redirects': 0,
        'final_url': url,
        'status_code': None,
        'reason': None,
    }

    try:
        response = requests.head(url, timeout=WEBSITE_TIMEOUT, allow_redirects=True)
        analysis['redirects'] = len(response.history)
        analysis['final_url'] = response.url
        analysis['status_code'] = response.status_code
        header_score, header_reasons = analyze_security_headers(response.headers)
        analysis['security_header_score'] = header_score
        analysis['security_header_reasons'] = header_reasons

        if response.status_code >= 400:
            analysis['reason'] = f'HTTP status {response.status_code}'
    except SSLError as exc:
        analysis['reason'] = f'SSL error: {exc}'
    except RequestException as exc:
        analysis['reason'] = f'Network error: {exc}'

    return analysis


def risk_score_from_analysis(analysis: Dict[str, object]) -> int:
    score = 0
    if not analysis['is_https']:
        score += 40
    if not analysis['ssl_valid']:
        score += 30
    if not analysis['dns_resolved']:
        score += 30
    if analysis['typosquatting']:
        score += 20
    score += max(0, 10 - analysis['security_header_score']) * 3
    score += min(20, analysis['redirects'] * 5)
    if analysis['status_code'] and analysis['status_code'] >= 400:
        score += 20
    return min(100, score)


def classify_website(analysis: Dict[str, object]) -> Tuple[str, float, str]:
    risk = risk_score_from_analysis(analysis)
    if risk >= 50:
        label = 'MALICIOUS'
    else:
        label = 'REAL'

    confidence = max(0.0, 100.0 - risk)
    reasons = []
    if not analysis['is_https']:
        reasons.append('HTTPS disabled')
    if not analysis['ssl_valid']:
        reasons.append('Invalid SSL certificate')
    if not analysis['dns_resolved']:
        reasons.append('DNS resolution failed')
    if analysis['typosquatting']:
        reasons.append(analysis['typosquatting_reason'])
    if analysis['redirects'] > 1:
        reasons.append('Multiple redirects detected')
    if analysis['security_header_reasons']:
        reasons.extend(analysis['security_header_reasons'])
    if analysis['status_code'] and analysis['status_code'] >= 400:
        reasons.append(f'HTTP status {analysis['status_code']}')

    reason_text = 'Trusted Domain' if label == 'REAL' and not reasons else '; '.join(reasons)
    return label, round(confidence, 1), reason_text
