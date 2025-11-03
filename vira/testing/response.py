"""
TestResponse class for examining HTTP responses in tests.
"""

import json as json_module
from typing import Any, Dict


class TestResponse:
    """Response object from TestClient requests with convenient testing methods."""

    def __init__(
        self,
        status_code: int,
        headers: Dict[str, str],
        content: bytes,
        request_url: str = "",
    ):
        """
        Initialize TestResponse.

        Args:
            status_code: HTTP status code
            headers: Response headers as dict
            content: Raw response body as bytes
            request_url: Original request URL for debugging
        """
        self.status_code = status_code
        self.headers = headers
        self.content = content
        self.request_url = request_url

    def text(self) -> str:
        """Response content as decoded text."""
        return self.content.decode("utf-8")

    def json(self) -> Any:
        """Parse response content as JSON."""
        try:
            return json_module.loads(self.text())
        except json_module.JSONDecodeError as e:
            raise ValueError(f"Response is not valid JSON: {e}")

    def body(self) -> bytes:
        """Raw response body as bytes."""
        return self.content

    @property
    def ok(self) -> bool:
        """True if status code is 200-299."""
        return 200 <= self.status_code < 300

    def __repr__(self) -> str:
        return f"<TestResponse {self.status_code}>"
