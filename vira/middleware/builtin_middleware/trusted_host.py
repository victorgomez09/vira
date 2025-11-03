"""
Trusted Host middleware for Vira.
Compatible with FastAPI's TrustedHostMiddleware interface.
"""

from typing import List, Optional, Callable, Awaitable
from ..middleware_chain import MiddlewareCallable
from ...response import Response
from ...request import Request


class TrustedHostMiddleware:
    """
    Trusted host middleware.

    Compatible with FastAPI's TrustedHostMiddleware interface.
    """

    def __init__(self, allowed_hosts: List[str] | None = None):
        """
        Initialize trusted host middleware.

        Args:
            allowed_hosts: List of allowed host patterns. Use ["*"] to allow all.
            www_redirect: Whether to redirect www subdomain to non-www.
        """
        self.allowed_hosts = set(allowed_hosts or [])

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """the middleware callable."""

        host = request.headers.get("host")

        if not self._is_host_allowed(host):
            return Response("Invalid host header", status_code=400)

        return await call_next(request)

    def _is_host_allowed(self, host: Optional[str]) -> bool:
        """Check if host is allowed."""
        if not host:
            return False

        if "*" in self.allowed_hosts:
            return True

        if host in self.allowed_hosts:
            return True

        # Check for wildcard patterns
        for allowed_host in self.allowed_hosts:
            if allowed_host.startswith("*."):
                domain = allowed_host[2:]  # Remove "*."
                if host.endswith("." + domain) or host == domain:
                    return True

        return False
