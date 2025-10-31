"""
Vira Middleware Package

This package provides the middleware system for Vira applications.
Middleware allows you to process requests and responses in a pipeline fashion.
"""

from .middlewarechain import MiddlewareChain, MiddlewareCallable

__all__ = ["MiddlewareChain", "MiddlewareCallable"]

# Import builtin middleware
from .builtin_middleware import (
    CORSMiddleware,
    GZipMiddleware,
    HTTPSRedirectMiddleware,
    TrustedHostMiddleware,
    ExceptionMiddleware,
)
