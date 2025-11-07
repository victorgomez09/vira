
"""Define security-related HTTP headers to be added to responses."""
from typing import Awaitable, Callable
from vira.request.request import Request
from vira.response import Response

DEFAULT_SECURITY_HEADERS = {
    # 1. Prevents Clickjacking. Disallows the page to be framed.
    "X-Frame-Options": "DENY",

    # 2. Prevents MIME-type sniffing (that the browser "guesses" the Content-Type).
    "X-Content-Type-Options": "nosniff",

    # 3. Enables the browser's native XSS filter.
    "X-XSS-Protection": "1; mode=block",

    # 4. Controls how much referrer information is sent.
    # 'strict-origin-when-cross-origin' is a good balance between security and usability.
    "Referrer-Policy": "strict-origin-when-cross-origin",
}

class HttpHeadersMiddleware:
    """Middleware to add security-related HTTP headers to responses."""

    def __init__(
        self,
        headers: dict = None,
        hsts_max_age: int = 31536000,
        enable_hsts: bool = True
    ):
        """Initialize http headers middleware and HSTS settings."""
        self.headers = DEFAULT_SECURITY_HEADERS.copy()
        if headers:
            self.headers.update(headers)
            
        self.enable_hsts = enable_hsts
        if self.enable_hsts:
            # HSTS is only included if HTTPS is used.
            hsts_value = f"max-age={hsts_max_age}; includeSubDomains"
            self.headers["Strict-Transport-Security"] = hsts_value
        
    async def __call__(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        """
        Process the request, call the next one in the chain, and then
        add the security headers to the response.
        """
        response = await call_next(request)

        for name, value in self.headers.items():
            is_hsts = (name == "Strict-Transport-Security")
            
            if is_hsts:
                if request.scheme.lower() == "https":
                    response.headers[name] = value
            else:
                response.headers[name] = value
                
        return response