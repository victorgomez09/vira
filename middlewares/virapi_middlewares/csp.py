from typing import Callable, Awaitable, Dict, Union
from virapi.request import Request
from virapi.response import Response

# Type for CSP policy configuration (dictionary of directives)
CSPPolicy = Dict[str, Union[str, list]]

class CSPMiddleware:
    """
    Middleware to inject the Content-Security-Policy (CSP) header
    into the response.

    Uses 'Content-Security-Policy-Report-Only' by default to avoid 
    immediately blocking resources in production, only allowing monitoring.
    """

    def __init__(
        self,
        policy: CSPPolicy = None,
        report_uri: str = None,
        report_only: bool = True
    ):
        """
        Initializes the CSP middleware.

        Args:
            policy: Dictionary of CSP directives (e.g., {"default-src": ["'self'", "cdn.example.com"]}).
            report_uri: URI where the browser should send violation reports.
            report_only: If True, uses 'Content-Security-Policy-Report-Only'. 
                         If False, uses 'Content-Security-Policy' (strict blocking mode).
        """
        self.report_uri = report_uri
        self.header_name = "Content-Security-Policy-Report-Only" if report_only else "Content-Security-Policy"

        # Define a strict base policy if none is provided
        if policy is None:
            self.policy = {
                "default-src": ["'self'"], # Allows resources only from the same origin
                "script-src": ["'self'", "'unsafe-inline'"], # 'unsafe-inline' is for compatibility, should be avoided
                "style-src": ["'self'", "'unsafe-inline'"],
                "img-src": ["'self'", "data:"], # Allows own images and base64
                "connect-src": ["'self'"],
            }
        else:
            self.policy = policy
            
        self.csp_string = self._build_csp_string()

    def _build_csp_string(self) -> str:
        """
        Converts the policy dictionary into the CSP header string.
        """
        directives = []
        
        # 1. Process standard directives
        for directive, sources in self.policy.items():
            if isinstance(sources, list):
                # Join the list of sources with spaces
                source_str = " ".join(sources)
            else:
                # If the source is a string (e.g., "'self'")
                source_str = sources
            
            directives.append(f"{directive} {source_str}")
        
        # 2. Add Report directive if URI was configured
        if self.report_uri:
            directives.append(f"report-uri {self.report_uri}")
            
        # Join all directives with semicolon
        return "; ".join(directives)

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Processes the request and adds the CSP header to the response.
        """
        
        # 1. Execute the rest of the middleware chain and the final endpoint.
        response = await call_next(request)

        # 2. CSP Header Injection
        # Ensure the header has not been set already
        if self.header_name not in response.headers:
            response.headers[self.header_name] = self.csp_string
            
        return response