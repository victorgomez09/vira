"""
TestClient class for executing HTTP requests against virapi applications.
"""

import asyncio
from typing import Dict, Optional

from .request import TestRequest
from .response import TestResponse


class TestClient:
    """
    HTTP test client for virapi applications.

    Provides a clean interface for testing HTTP endpoints by executing
    TestRequest objects against virapi applications and returning
    TestResponse objects.
    """

    def __init__(self, app):
        """
        Initialize TestClient with a virapi application.

        Args:
            app: virapi application instance
        """
        self.app = app

    def execute(self, method: str, url: str, request: TestRequest) -> TestResponse:
        """
        Execute a TestRequest against the application.

        Args:
            method: HTTP method (GET, POST, PUT, etc.)
            url: Request URL path
            request: TestRequest object with request configuration

        Returns:
            TestResponse object with the response data
        """
        # Build request components
        query_string = request.build_query_string()
        full_url = request.build_full_url(url)
        request_body, body_headers = request.build_body()
        request_headers = request.build_headers()

        # Merge body headers with request headers (request headers take precedence)
        final_headers = {}
        final_headers.update(body_headers)
        final_headers.update(request_headers)

        # Convert headers to ASGI format
        asgi_headers = []
        for key, value in final_headers.items():
            asgi_headers.append(
                [key.lower().encode("utf-8"), str(value).encode("utf-8")]
            )

        # Build ASGI scope
        scope = {
            "type": "http",
            "method": method.upper(),
            "path": url,
            "query_string": query_string,
            "headers": asgi_headers,
        }

        # Execute the request
        try:
            # Check if we're in an async context (pytest-asyncio)
            loop = asyncio.get_running_loop()
            # Use asyncio.create_task and wait for completion
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    asyncio.run, self._make_request(scope, request_body, full_url)
                )
                return future.result()
        except RuntimeError:
            # No event loop running, create one
            return asyncio.run(self._make_request(scope, request_body, full_url))

    async def _make_request(
        self, scope: dict, body: bytes, request_url: str = ""
    ) -> TestResponse:
        """Execute the request against the ASGI application."""
        # Ensure middleware chain is built
        if not getattr(self.app, "_middleware_built", False):
            await self.app._build_middleware_chain()

        response_data = {}
        body_parts = []

        # Define ASGI receive and send callables
        async def receive():
            return {
                "type": "http.request",
                "body": body,
                "more_body": False,
            }

        async def send(message):
            if message["type"] == "http.response.start":
                response_data["status"] = message["status"]
                response_data["headers"] = message["headers"]
            elif message["type"] == "http.response.body":
                body_parts.append(message.get("body", b""))
                response_data["more_body"] = message.get("more_body", False)

        # Execute the request
        await self.app(scope, receive, send)

        # Parse response
        status_code = response_data.get("status", 500)
        headers = response_data.get("headers", [])

        # Convert headers to dict
        header_dict = {}
        for header_pair in headers:
            if len(header_pair) == 2:
                key, value = header_pair
                if isinstance(key, bytes):
                    key = key.decode("utf-8")
                if isinstance(value, bytes):
                    value = value.decode("utf-8")
                header_dict[key] = value

        # Combine body parts
        response_body = b"".join(body_parts)

        return TestResponse(status_code, header_dict, response_body, request_url)

    # Convenience methods for executing common requests
    def get(self, url: str, request: Optional[TestRequest] = None) -> TestResponse:
        """Execute a GET request."""
        if request is None:
            request = TestRequest()
        return self.execute("GET", url, request)

    def post(self, url: str, request: Optional[TestRequest] = None) -> TestResponse:
        """Execute a POST request."""
        if request is None:
            request = TestRequest()
        return self.execute("POST", url, request)

    def put(self, url: str, request: Optional[TestRequest] = None) -> TestResponse:
        """Execute a PUT request."""
        if request is None:
            request = TestRequest()
        return self.execute("PUT", url, request)

    def patch(self, url: str, request: Optional[TestRequest] = None) -> TestResponse:
        """Execute a PATCH request."""
        if request is None:
            request = TestRequest()
        return self.execute("PATCH", url, request)

    def delete(self, url: str, request: Optional[TestRequest] = None) -> TestResponse:
        """Execute a DELETE request."""
        if request is None:
            request = TestRequest()
        return self.execute("DELETE", url, request)

    def head(self, url: str, request: Optional[TestRequest] = None) -> TestResponse:
        """Execute a HEAD request."""
        if request is None:
            request = TestRequest()
        return self.execute("HEAD", url, request)

    def options(self, url: str, request: Optional[TestRequest] = None) -> TestResponse:
        """Execute an OPTIONS request."""
        if request is None:
            request = TestRequest()
        return self.execute("OPTIONS", url, request)
