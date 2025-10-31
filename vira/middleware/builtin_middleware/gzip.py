"""
GZip compression middleware for Vira.
Compatible with FastAPI's GZipMiddleware interface.
"""

import gzip
from typing import Callable, Awaitable
from ...request import Request
from ...response import Response


class GZipMiddleware:
    """
    GZip compression middleware.
    """

    def __init__(self, minimum_size: int = 500, compresslevel: int = 9):
        """
        Initialize GZip middleware.

        Args:
            minimum_size: Minimum response size to compress (bytes).
            compresslevel: Compression level (0-9, 9 is highest compression).
        """
        self.minimum_size = minimum_size
        self.compresslevel = compresslevel

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """the middleware callable."""

        response = await call_next(request)

        # Check if client accepts gzip encoding
        accept_encoding = request.headers.get("accept-encoding", "")
        if "gzip" not in accept_encoding.lower():
            return response

        # Check if response should be compressed
        if not self._should_compress(response):
            return response

        # Compress the response
        return self._compress_response(response)

    def _should_compress(self, response: Response) -> bool:
        """Check if response should be compressed."""
        # Skip if already compressed
        if "content-encoding" in response.headers:
            return False

        # Check content type
        content_type = response.headers.get("content-type", "")
        compressible_types = [
            "text/",
            "application/json",
            "application/javascript",
            "application/xml",
            "application/atom+xml",
            "application/rss+xml",
        ]

        if not any(content_type.startswith(ct) for ct in compressible_types):
            return False

        # Check minimum size
        body_size = (
            len(response.body)
            if isinstance(response.body, bytes)
            else len(response.body.encode())
        )
        return body_size >= self.minimum_size

    def _compress_response(self, response: Response) -> Response:
        """Compress response body with gzip."""
        # Get body as bytes
        if isinstance(response.body, str):
            body_bytes = response.body.encode("utf-8")
        else:
            body_bytes = response.body

        # Compress
        compressed_body = gzip.compress(body_bytes, compresslevel=self.compresslevel)

        # Create new response with compressed body
        compressed_response = Response(
            compressed_body,
            status_code=response.status_code,
            headers=response.headers.copy(),
        )

        # Add compression headers
        compressed_response.headers["content-encoding"] = "gzip"
        compressed_response.headers["content-length"] = str(len(compressed_body))

        return compressed_response
