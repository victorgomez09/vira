"""
Response class for virapi framework.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, Union

from .status import HTTPStatus


class Response:
    """
    Response object for building HTTP responses with automatic content type detection.

    Supports:
    - Automatic content type detection (JSON, HTML, plain text)
    - Custom status codes and headers
    - Method chaining for header setting
    - Conversion to ASGI response format
    """

    def __init__(
        self,
        content: Union[str, bytes, dict, list, int, float] = "",
        status_code: Union[int, HTTPStatus] = HTTPStatus.HTTP_200_OK,
        headers: Optional[Dict[str, str]] = None,
        content_type: Optional[str] = None,
    ):
        """
        Initialize Response object.

        Args:
            content: Response content (auto-converts dict/list to JSON)
            status_code: HTTP status code (int or HTTPStatus enum)
            headers: Additional response headers
            content_type: Explicit content type (auto-detected if not provided)
        """
        self.status_code = int(status_code)  # Convert HTTPStatus enum to int
        self.headers = headers or {}
        self._cookies = []  # List to store Set-Cookie headers

        # Convert content to bytes and determine content type
        self.body, detected_content_type = self._process_content(content)

        # Set content type (explicit takes precedence over auto-detected)
        if content_type:
            self.headers["content-type"] = content_type
        elif detected_content_type and "content-type" not in self.headers:
            self.headers["content-type"] = detected_content_type

    def _process_content(self, content: Any) -> tuple[bytes, Optional[str]]:
        """
        Process content and determine appropriate content type.

        Args:
            content: Raw content of various types

        Returns:
            Tuple of (processed_bytes, detected_content_type)
        """
        if isinstance(content, (dict, list)):
            # JSON content
            body = json.dumps(content, ensure_ascii=False).encode("utf-8")
            content_type = "application/json; charset=utf-8"
        elif isinstance(content, str):
            body = content.encode("utf-8")
            # Auto-detect HTML vs plain text
            if content.strip().startswith(("<!DOCTYPE", "<html", "<HTML")):
                content_type = "text/html; charset=utf-8"
            elif any(
                tag in content.lower()
                for tag in ["<h1>", "<h2>", "<p>", "<div>", "<span>", "<body>"]
            ):
                content_type = "text/html; charset=utf-8"
            else:
                content_type = "text/plain; charset=utf-8"
        elif isinstance(content, bytes):
            body = content
            content_type = "application/octet-stream"
        elif isinstance(content, (int, float)):
            # Convert numbers to string
            body = str(content).encode("utf-8")
            content_type = "text/plain; charset=utf-8"
        elif content is None:
            body = b""
            content_type = "text/plain; charset=utf-8"
        else:
            # Convert anything else to string
            body = str(content).encode("utf-8")
            content_type = "text/plain; charset=utf-8"

        return body, content_type

    def set_header(self, name: str, value: str) -> "Response":
        """
        Set a response header (supports method chaining).

        Args:
            name: Header name
            value: Header value

        Returns:
            self for method chaining
        """
        self.headers[name] = value
        return self

    def set_cookie(
        self,
        name: str,
        value: str,
        max_age: Optional[int] = None,
        expires: Optional[datetime] = None,
        path: str = "/",
        domain: Optional[str] = None,
        secure: bool = False,
        httponly: bool = False,
        samesite: Optional[str] = None,
    ) -> "Response":
        """
        Set a cookie (supports method chaining).

        Args:
            name: Cookie name
            value: Cookie value
            max_age: Cookie lifetime in seconds
            expires: Cookie expiration datetime
            path: Cookie path
            domain: Cookie domain
            secure: Whether cookie requires HTTPS
            httponly: Whether cookie is HTTP-only
            samesite: SameSite attribute ('Strict', 'Lax', or 'None')

        Returns:
            self for method chaining
        """
        cookie_parts = [f"{name}={value}"]

        if max_age is not None:
            cookie_parts.append(f"Max-Age={max_age}")
        if expires is not None:
            # Format: Wdy, DD Mon YYYY HH:MM:SS GMT
            expires_str = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")
            cookie_parts.append(f"Expires={expires_str}")
        if path:
            cookie_parts.append(f"Path={path}")
        if domain:
            cookie_parts.append(f"Domain={domain}")
        if secure:
            cookie_parts.append("Secure")
        if httponly:
            cookie_parts.append("HttpOnly")
        if samesite:
            cookie_parts.append(f"SameSite={samesite}")

        cookie_header = "; ".join(cookie_parts)
        self._cookies.append(cookie_header)

        return self

    def delete_cookie(
        self,
        name: str,
        path: str = "/",
        domain: Optional[str] = None,
    ) -> "Response":
        """
        Delete a cookie by setting its Max-Age to 0 (supports method chaining).

        Args:
            name: Cookie name to delete
            path: Cookie path (must match the original)
            domain: Cookie domain (must match the original)

        Returns:
            self for method chaining
        """
        return self.set_cookie(
            name=name,
            value="",
            max_age=0,
            path=path,
            domain=domain,
        )

    def clear_cookies(self) -> "Response":
        """
        Clear all cookies that would be set by this response (supports method chaining).

        Returns:
            self for method chaining
        """
        self._cookies.clear()
        return self

    def to_asgi_response(self) -> Dict[str, Any]:
        """
        Convert to ASGI response format.

        Returns:
            Dictionary with 'status', 'headers', and 'body' keys
        """
        # Convert headers to ASGI format (list of [name, value] byte pairs)
        asgi_headers = []
        for name, value in self.headers.items():
            asgi_headers.append(
                [name.lower().encode("utf-8"), str(value).encode("utf-8")]
            )

        # Add Set-Cookie headers (multiple cookies require multiple headers)
        for cookie in self._cookies:
            asgi_headers.append([b"set-cookie", cookie.encode("utf-8")])

        return {"status": self.status_code, "headers": asgi_headers, "body": self.body}

    def __repr__(self) -> str:
        return f"<Response {self.status_code}>"


# Convenience functions for common response types
def text_response(
    content: str,
    status_code: Union[int, HTTPStatus] = HTTPStatus.HTTP_200_OK,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """Create a plain text response."""
    return Response(
        content,
        status_code=status_code,
        headers=headers,
        content_type="text/plain; charset=utf-8",
    )


def html_response(
    content: str,
    status_code: Union[int, HTTPStatus] = HTTPStatus.HTTP_200_OK,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """Create an HTML response."""
    return Response(
        content,
        status_code=status_code,
        headers=headers,
        content_type="text/html; charset=utf-8",
    )


def json_response(
    content: Union[dict, list],
    status_code: Union[int, HTTPStatus] = HTTPStatus.HTTP_200_OK,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """Create a JSON response."""
    return Response(
        content,
        status_code=status_code,
        headers=headers,
        content_type="application/json; charset=utf-8",
    )


def redirect_response(
    url: str,
    status_code: Union[int, HTTPStatus] = HTTPStatus.HTTP_302_FOUND,
    headers: Optional[Dict[str, str]] = None,
) -> Response:
    """Create a redirect response."""
    redirect_headers = {"location": url}
    if headers:
        redirect_headers.update(headers)

    return Response("", status_code=status_code, headers=redirect_headers)
