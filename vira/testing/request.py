"""
TestRequest class for building HTTP requests with an API.
"""

import json as json_module
import mimetypes
import uuid
from typing import Any, Dict, Optional, Union, IO, Tuple
from urllib.parse import urlencode


class TestRequest:
    """Builder class for constructing HTTP requests with an API."""

    def __init__(self):
        """
        Initialize TestRequest.

        Note: Method and URL are now passed when executing the request,
        making TestRequest instances reusable across different requests.
        """
        self._params: Dict[str, Any] = {}
        self._headers: Dict[str, str] = {}
        self._cookies: Dict[str, str] = {}
        self._body_data: Optional[Union[str, bytes, Dict[str, Any]]] = None
        self._json: Optional[Any] = None
        self._files: Dict[str, Tuple[str, bytes, str]] = {}

    def set_query_params(self, **params) -> "TestRequest":
        """
        Add query parameters to the URL.

        Args:
            **params: Query parameters as keyword arguments

        Returns:
            Self for chaining
        """
        self._params.update(params)
        return self

    def set_form_data(self, **data) -> "TestRequest":
        """
        Set form data for the request body (application/x-www-form-urlencoded).

        Args:
            **data: Form fields as keyword arguments

        Returns:
            Self for chaining
        """
        if not isinstance(self._body_data, dict):
            self._body_data = {}
        self._body_data.update(data)
        return self

    def set_raw_body(self, body: Union[str, bytes]) -> "TestRequest":
        """
        Set raw request body data.

        Args:
            body: Raw body content as string or bytes

        Returns:
            Self for chaining
        """
        self._body_data = body
        return self

    def set_json_body(self, json_data: Any) -> "TestRequest":
        """
        Set JSON payload for the request body.

        Args:
            json_data: Data to serialize as JSON

        Returns:
            Self for chaining
        """
        self._json = json_data
        return self

    def upload_file(
        self,
        field_name: str,
        filename: str,
        file_content: Union[str, bytes, IO],
        content_type: Optional[str] = None,
    ) -> "TestRequest":
        """
        Add a single file upload (creates multipart/form-data request).

        Args:
            field_name: The form field name for the file
            filename: The filename to use for the upload
            file_content: File content as string, bytes, or file-like object
            content_type: MIME type (auto-detected from filename if None)

        Returns:
            Self for chaining
        """
        # Handle file-like objects by reading their content
        if hasattr(file_content, "read"):
            content: Union[str, bytes] = file_content.read()
        else:
            content = file_content

        # Ensure content is bytes for consistency
        if isinstance(content, str):
            content = content.encode("utf-8")

        # Guess content type if not provided
        if content_type is None:
            content_type = (
                mimetypes.guess_type(filename)[0] or "application/octet-stream"
            )

        # Store as a 3-tuple with all info predetermined
        self._files[field_name] = (filename, content, content_type)
        return self

    def set_headers(self, **headers) -> "TestRequest":
        """
        Add custom headers to the request.

        Args:
            **headers: Headers as keyword arguments

        Returns:
            Self for chaining
        """
        self._headers.update(headers)
        return self

    def set_header(self, name: str, value: str) -> "TestRequest":
        """
        Add a single custom header to the request.

        Args:
            name: Header name
            value: Header value

        Returns:
            Self for chaining
        """
        self._headers[name] = value
        return self

    def set_cookies(self, **cookies) -> "TestRequest":
        """
        Add cookies to the request.

        Args:
            **cookies: Cookies as keyword arguments

        Returns:
            Self for chaining
        """
        self._cookies.update(cookies)
        return self

    def set_cookie(self, name: str, value: str) -> "TestRequest":
        """
        Add a single cookie to the request.

        Args:
            name: Cookie name
            value: Cookie value

        Returns:
            Self for chaining
        """
        self._cookies[name] = value
        return self

    def set_bearer_auth(self, token: str) -> "TestRequest":
        """
        Set Bearer token authentication.

        Args:
            token: JWT or other bearer token

        Returns:
            Self for chaining
        """
        self._headers["Authorization"] = f"Bearer {token}"
        return self

    def set_basic_auth(self, username: str, password: str) -> "TestRequest":
        """
        Set HTTP Basic authentication.

        Args:
            username: Username for basic auth
            password: Password for basic auth

        Returns:
            Self for chaining
        """
        import base64

        credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
        self._headers["Authorization"] = f"Basic {credentials}"
        return self

    def build_query_string(self) -> bytes:
        """Build query string from parameters."""
        if not self._params:
            return b""

        # Handle nested params and lists
        query_items = []
        for key, value in self._params.items():
            if isinstance(value, (list, tuple)):
                for item in value:
                    query_items.append((key, str(item)))
            else:
                query_items.append((key, str(value)))

        return urlencode(query_items).encode("utf-8")

    def build_full_url(self, url: str) -> str:
        """Build full URL with query string."""
        query_string = self.build_query_string()
        if query_string:
            return f"{url}?{query_string.decode('utf-8')}"
        return url

    def build_body(self) -> Tuple[bytes, Dict[str, str]]:
        """
        Build request body and determine content headers.

        Returns:
            Tuple of (body_bytes, additional_headers)
        """
        additional_headers = {}
        request_body = b""

        # Check if user already provided Content-Type
        user_content_type = self._headers.get("Content-Type") or self._headers.get(
            "content-type"
        )

        if self._json is not None:
            # JSON payload
            request_body = json_module.dumps(self._json, ensure_ascii=False).encode(
                "utf-8"
            )
            if not user_content_type:
                additional_headers["Content-Type"] = "application/json; charset=utf-8"

        elif self._files:
            # Multipart form data with file uploads
            form_data = self._body_data if isinstance(self._body_data, dict) else {}
            boundary = "TestClient" + uuid.uuid4().hex
            request_body = self._build_multipart_body(form_data, self._files, boundary)
            if not user_content_type:
                additional_headers["Content-Type"] = (
                    f"multipart/form-data; boundary={boundary}"
                )

        elif self._body_data:
            if isinstance(self._body_data, dict):
                # Form data
                request_body = urlencode(self._body_data).encode("utf-8")
                if not user_content_type:
                    additional_headers["Content-Type"] = (
                        "application/x-www-form-urlencoded"
                    )
            elif isinstance(self._body_data, str):
                request_body = self._body_data.encode("utf-8")
                if not user_content_type:
                    additional_headers["Content-Type"] = "text/plain; charset=utf-8"
            elif isinstance(self._body_data, bytes):
                request_body = self._body_data
                if not user_content_type:
                    additional_headers["Content-Type"] = "application/octet-stream"

        # Set content length
        if request_body:
            additional_headers["Content-Length"] = str(len(request_body))

        return request_body, additional_headers

    def build_headers(self) -> Dict[str, str]:
        """Build final headers dict including cookies."""
        final_headers = {}
        final_headers.update(self._headers)

        # Add cookie header
        if self._cookies:
            cookie_header = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
            final_headers["Cookie"] = cookie_header

        return final_headers

    def _build_multipart_body(
        self,
        data: Dict[str, Any],
        files: Dict[str, Tuple[str, bytes, str]],
        boundary: str,
    ) -> bytes:
        """Build multipart/form-data body for file uploads."""
        body_parts = []

        # Add form fields
        for key, value in data.items():
            part = f"--{boundary}\r\n"
            part += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
            part += f"{value}\r\n"
            body_parts.append(part.encode("utf-8"))

        # Add files - now simplified since all files are (filename, content, content_type) tuples
        for key, (filename, content, content_type) in files.items():
            part = f"--{boundary}\r\n"
            part += f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
            part += f"Content-Type: {content_type}\r\n\r\n"
            body_parts.append(part.encode("utf-8"))

            # Ensure content is bytes
            if isinstance(content, str):
                content = content.encode("utf-8")
            body_parts.append(content)
            body_parts.append(b"\r\n")

        # Add final boundary
        body_parts.append(f"--{boundary}--\r\n".encode("utf-8"))

        return b"".join(body_parts)

    def __repr__(self) -> str:
        return f"<TestRequest {len(self._headers)} headers, {len(self._params)} params>"
