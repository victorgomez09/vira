"""
Built-in middleware for Vira.
Compatible with FastAPI middleware interfaces.
"""

from .cors import CORSMiddleware
from .gzip import GZipMiddleware
from .https_redirect import HTTPSRedirectMiddleware
from .trusted_host import TrustedHostMiddleware
from .exception import ExceptionMiddleware

__all__ = [
    "CORSMiddleware",
    "GZipMiddleware",
    "HTTPSRedirectMiddleware",
    "TrustedHostMiddleware",
    "ExceptionMiddleware",
]
