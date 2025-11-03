"""
CORS (Cross-Origin Resource Sharing) middleware for Vira.
Compatible with FastAPI's CORSMiddleware interface.
"""

from typing import Optional, Sequence, Callable, Awaitable
from ...response import Response
from ...request import Request
import re

ALL_METHODS = ("DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT")


class CORSMiddleware:
    """
    CORS middleware that adds CORS headers to responses.

    Compatible with FastAPI's CORSMiddleware interface.
    """

    def __init__(
        self,
        allow_origins: Sequence[str] = [],
        allow_methods: Sequence[str] = ["GET"],
        allow_headers: Sequence[str] = [],
        allow_credentials: bool = False,
        allow_origin_regex: Optional[str] = None,
        expose_headers: Sequence[str] = [],
        max_age: int = 600,
    ):
        """
        Initialize CORS middleware.

        Args:
            allow_origins: List of allowed origins. Use ["*"] for all origins.
            allow_methods: List of allowed HTTP methods.
            allow_headers: List of allowed headers.
            allow_credentials: Whether to allow credentials.
            allow_origin_regex: Regex pattern for allowed origins.
            expose_headers: List of headers to expose to the browser.
            max_age: Maximum age for preflight cache.
        """
        if "*" in allow_methods:
            allow_methods = ALL_METHODS

        compiled_allow_origin_regex = None
        if allow_origin_regex is not None:
            compiled_allow_origin_regex = re.compile(allow_origin_regex)

        self.allow_origins = set(allow_origins)
        self.allow_all_origins = "*" in allow_origins
        self.allow_methods = set([m.upper() for m in allow_methods])
        self.allow_headers = set(allow_headers)
        self.allow_all_headers = "*" in allow_headers
        self.allow_credentials = allow_credentials
        self.allow_origin_regex = compiled_allow_origin_regex
        self.expose_headers = set(expose_headers)
        self.max_age = max_age

        # Convert to lowercase for case-insensitive comparison
        self.allow_headers_lower = {h.lower() for h in self.allow_headers}

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """the middleware callable."""

        origin = request.headers.get("origin")
        method = request.method

        # Handle preflight requests
        if method == "OPTIONS":
            return self._handle_preflight(request, origin)

        # Handle actual requests
        response = await call_next(request)
        return self._add_cors_headers(response, origin)

    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed."""

        if not origin:
            return False

        # If allow_credentials is False, we can allow all origins if "*" is specified
        # when allow_credentials is True, only specific origins can be allowed
        if self.allow_all_origins and not self.allow_credentials:
            return True

        if origin in self.allow_origins:
            return True

        if self.allow_origin_regex:
            return bool(self.allow_origin_regex.match(origin))

        return False

    def _handle_preflight(self, request, origin: Optional[str]) -> Response:
        """Handle CORS preflight requests."""
        response = Response("", status_code=204)  # 204 = No Content

        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"

            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

            # Handle requested method
            requested_method = request.headers.get("access-control-request-method")
            if requested_method and requested_method.upper() in self.allow_methods:
                response.headers["Access-Control-Allow-Methods"] = ", ".join(
                    self.allow_methods
                )

            # Handle requested headers
            requested_headers = request.headers.get("access-control-request-headers")
            if requested_headers:
                if self.allow_all_headers:
                    response.headers["Access-Control-Allow-Headers"] = requested_headers
                else:
                    headers = [h.strip().lower() for h in requested_headers.split(",")]
                    if all(
                        h in self.allow_headers_lower or not self.allow_headers
                        for h in headers
                    ):
                        response.headers["Access-Control-Allow-Headers"] = (
                            requested_headers
                        )

            response.headers["Access-Control-Max-Age"] = str(self.max_age)

        return response

    def _add_cors_headers(self, response: Response, origin: Optional[str]) -> Response:
        """Add CORS headers to response."""
        if self._is_origin_allowed(origin):
            response.headers["Access-Control-Allow-Origin"] = origin or "*"

            if self.allow_credentials:
                response.headers["Access-Control-Allow-Credentials"] = "true"

            if self.expose_headers:
                response.headers["Access-Control-Expose-Headers"] = ", ".join(
                    self.expose_headers
                )

        return response
