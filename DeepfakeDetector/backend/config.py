from pathlib import Path
from typing import Set

ROOT_DIR = Path(__file__).resolve().parent
WEIGHTS_DIR = ROOT_DIR / 'weights'
XCEPTION_WEIGHTS = WEIGHTS_DIR / 'xception.pth'
EFFICIENTNET_WEIGHTS = WEIGHTS_DIR / 'efficientnet_b0.pth'
SWIN_WEIGHTS = WEIGHTS_DIR / 'swin_transformer.pth'
RESNET_WEIGHTS = WEIGHTS_DIR / 'resnet34.pth'

SUPPORTED_IMAGE_EXTENSIONS: Set[str] = {'.jpg', '.jpeg', '.png', '.bmp', '.webp'}
SUPPORTED_VIDEO_EXTENSIONS: Set[str] = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
MAX_IMAGE_BYTES = 30 * 1024 * 1024
MAX_VIDEO_BYTES = 200 * 1024 * 1024
VIDEO_FRAME_COUNT = 16
WEBSITE_TIMEOUT = 15

SUSPICIOUS_DOMAIN_KEYWORDS = {
    'login', 'secure', 'account', 'bank', 'verify', 'update', 'confirm', 'online', 'signin', 'paypal',
    'appleid', 'microsoft', 'security', 'support', 'billing', 'webscr', 'ebayisapi', 'google', 'amazon'
}

SUSPICIOUS_PATH_KEYWORDS = {
    'login', 'signin', 'secure', 'verify', 'update', 'account', 'password', 'confirm', 'bank', 'checkout',
    'billing', 'payment', 'authenticate', 'unlock'
}

SECURITY_HEADERS = [
    'strict-transport-security',
    'content-security-policy',
    'x-frame-options',
    'x-content-type-options',
    'referrer-policy',
    'permissions-policy',
]
