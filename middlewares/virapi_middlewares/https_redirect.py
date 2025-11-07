"""
HTTPS Redirect middleware for virapi.
Compatible with FastAPI's HTTPSRedirectMiddleware interface.
"""

from virapi.middleware.middleware_chain import MiddlewareCallable
from virapi.response import redirect_response
from virapi.request import Request


class HTTPSRedirectMiddleware:
    """
    HTTPS redirect middleware.

    Compatible with FastAPI's HTTPSRedirectMiddleware interface.
    """

    def __init__(self):
        """Initialize HTTPS redirect middleware."""
        pass

    def __call__(self) -> MiddlewareCallable:
        """Return the middleware callable."""

        async def https_redirect_middleware(request: Request, call_next):
            # Check if request is already HTTPS
            if request.url.startswith("https://"):
                return await call_next(request)

            # Redirect to HTTPS
            https_url = request.url.replace("http://", "https://", 1)
            return redirect_response(
                url=https_url,
                status_code=307,  # Temporary Redirect
            )

        return https_redirect_middleware
