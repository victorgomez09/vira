"""
Request class for Vira framework.
"""

import json
import urllib.parse
import weakref
from typing import Dict, Any, Optional, List, Callable, Awaitable, TYPE_CHECKING

from .upload_file import UploadFile
from .multipart.parser import MultipartParser
from vira.state import State

if TYPE_CHECKING:
    # Import to avoid runtime cycles, only used for type checking
    from vira import Vira


class Request:
    """
    Request object that wraps ASGI scope and message for easier access to HTTP request data.

    Provides convenient access to:
    - HTTP method, path, headers
    - Query parameters with automatic parsing
    - Request body as text, bytes, JSON, multipart
    - Content type detection
    """

    # Global registry for cleanup tracking
    _active_requests = weakref.WeakSet()

    # Application-level configuration (set by Vira)
    max_in_memory_file_size: int = 1024 * 1024  # 1MB default
    temp_dir: Optional[str] = None

    # Types added so that handlers and middleware can see that Request has a reference to the app and the state
    app: Optional["Vira"]
    state: Optional[State]

    def __init__(
        self,
        scope: Dict[str, Any],
        receive: Callable[[], Awaitable[Dict[str, Any]]],
    ):
        """
        Initialize Request object from ASGI scope and receive callable.

        Args:
            scope: ASGI scope dictionary containing request metadata
            receive: ASGI receive callable for reading request body
        """
        self._scope = scope
        self._receive = receive
        self._body: Optional[bytes] = None
        self._form: Optional[Dict[str, str]] = None
        self._files: Optional[List[UploadFile]] = None
        self._query_params: Dict[str, str] | None = None
        self._query_params_multi_values: Dict[str, List[str]] | None = None
        self._json: Dict[str, Any] | None = None
        self._headers: Dict[str, str] | None = None
        self._url: str | None = None
        self._cookies: Dict[str, str] | None = None
        self.path_params: Dict[str, Any] = {}  # Dynamic path parameters
        self._body_loaded = False

        # Initialize attributes that can be filled by the application when building the Request
        self.app = None
        self.state = None

        # Add to cleanup registry
        Request._active_requests.add(self)

    @classmethod
    async def from_asgi(
        cls, scope: Dict[str, Any], receive: Callable[[], Awaitable[Dict[str, Any]]]
    ) -> "Request":
        """
        Factory method to create a Request object from ASGI 'scope' and 'receive' callable.
        It also loads the request body. This is an async method. The reason for this is that
        loading the body may involve awaiting on the 'receive' callable and thus cannot be done in __init__.

        Args:
            scope: ASGI scope dictionary
            receive: ASGI receive callable

        Returns:
            Request object
        """
        request = cls(scope, receive)
        await request.load_body()
        return request

    @classmethod
    def cleanup_all_active_requests(cls) -> int:
        """
        Clean up all active requests. Useful for application shutdown.
        For each active request, calls its cleanup_files method.
        Returns:
            Number of requests cleaned up
        """
        count = 0
        # Create a copy of the set to avoid modification during iteration
        requests_to_cleanup = list(cls._active_requests)
        for request in requests_to_cleanup:
            try:
                request.cleanup_files()
                count += 1
            except Exception:
                # Silent cleanup
                pass
        return count

    async def load_body(self) -> None:
        """
        Load the request body from the ASGI 'receive' callable.

        This method handles both regular and multipart requests.
        """
        if self._body_loaded:
            return

        self._body = await self._receive_complete_message(self._receive)
        # Determine content-type
        content_type = self.headers.get("content-type", "")
        if "multipart/form-data" in content_type:
            # Use simple multipart parsing logic
            # Extract boundary and parse
            boundary = MultipartParser.extract_boundary(content_type)
            if boundary:
                parser = MultipartParser()
                form_data, files = parser.parse(self._body, boundary)
                self._form = form_data
                self._files = files
            else:
                self._form = {}
                self._files = []
        else:
            # Parse form data for URL-encoded content
            if "application/x-www-form-urlencoded" in content_type:
                self._parse_form_data()

        self._body_loaded = True

    def body(self) -> bytes:
        """Raw request body as bytes"""
        if self._body is None:
            raise RuntimeError(
                "Request body has not been loaded. Call 'await request.load_body()' first."
            )
        return self._body

    def cleanup_files(self) -> None:
        """
        Clean up any temporary files associated with uploaded files.

        This method should be called when the request is no longer needed
        to ensure temporary files are properly removed.
        """
        if self._files:
            for upload_file in self._files:
                try:
                    upload_file.cleanup()  # Clean up temp file
                except Exception:
                    # Silent cleanup - don't let cleanup errors affect the application
                    pass

    def get_header(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a header value by name (case-insensitive).

        Args:
            name: Header name (case-insensitive)
            default: Default value if header not found

        Returns:
            Header value or default
        """
        return self.headers.get(name.lower(), default)

    def is_form(self) -> bool:
        """Check if the request has form content type"""
        content_type = self.content_type
        return (
            content_type is not None
            and "application/x-www-form-urlencoded" in content_type.lower()
        )

    def is_json(self) -> bool:
        """Check if the request has JSON content type"""
        content_type = self.content_type
        return content_type is not None and "application/json" in content_type.lower()

    def json(self) -> Any:
        """
        Parse request body as JSON.

        Returns:
            Parsed JSON data (dict, list, etc.)

        Raises:
            ValueError: If body is empty or contains invalid JSON
            RuntimeError: If body has not been loaded yet
        """
        if self._json is None:
            if self._body is None:
                raise RuntimeError(
                    "Request body has not been loaded. Call 'await request.load_body()' first."
                )
            if not self._body:
                raise ValueError("Request body is empty")
            try:
                self._json = json.loads(self._body.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON in request body: {e}")
        return self._json

    def text(self) -> str:
        """Request body decoded as UTF-8 text"""
        if self._body is None:
            raise RuntimeError(
                "Request body has not been loaded. Call 'await request.load_body()' first."
            )
        return self._body.decode("utf-8")

    @property
    def content_type(self) -> Optional[str]:
        """Content-Type header value, or None if not present"""
        return self.headers.get("content-type")

    @property
    def cookies(self) -> Dict[str, str]:
        """
        Cookies parsed from the Cookie header.

        For duplicate cookie names, the last value is kept.

        Returns:
            Dictionary of cookie names to values
        """

        if self._cookies is None:
            self._cookies = {}
            cookie_header = self.headers.get("cookie", "")
            if cookie_header:
                for cookie_pair in cookie_header.split(";"):
                    cookie_pair = cookie_pair.strip()
                    if "=" in cookie_pair:
                        name, value = cookie_pair.split("=", 1)
                        self._cookies[name.strip()] = value.strip()
        return self._cookies

    @property
    def files(self) -> List[UploadFile]:
        """List of files uploaded in a multipart/form-data request."""

        return self._files or []

    @property
    def form(self) -> Dict[str, str]:
        """Parsed form fields from the request body."""

        return self._form or {}

    @property
    def headers(self) -> Dict[str, str]:
        """
        Request headers as a case-insensitive dictionary.

        Returns:
            Dictionary with lowercase header names as keys
        """

        if self._headers is None:
            self._headers = {}
            for name, value in self._scope.get("headers", []):
                self._headers[name.decode().lower()] = value.decode()
        return self._headers

    @property
    def method(self) -> str:
        """HTTP method (GET, POST, PUT, DELETE, etc.)"""

        return self._scope.get("method", "GET")

    @property
    def path(self) -> str:
        """Request path (e.g., '/api/users')"""

        return self._scope.get("path", "/")

    @property
    def query_params(self) -> Dict[str, str]:
        """
        Query parameters parsed as a dictionary.

        For duplicate parameters, only the first value is kept.

        Example: '?page=1&limit=10&tags=python&tags=web' -> {'page': '1', 'limit': '10', 'tags': 'python'}

        Returns:
            Dictionary of query parameter names to values
        """

        if self._query_params is None:
            self._query_params = {}
            if self.query_string:
                parsed = urllib.parse.parse_qs(
                    self.query_string, keep_blank_values=True
                )
                for key, value_list in parsed.items():
                    self._query_params[key] = value_list[0] if value_list else ""
        return self._query_params

    @property
    def query_params_multi_values(self) -> Dict[str, List[str]]:
        """
        Query parameters parsed as a dictionary with multiple values.

        All values for each parameter are preserved as lists.
        Example: '?page=1&limit=10&tags=python&tags=web' -> {'page': ['1'], 'limit': ['10'], 'tags': ['python', 'web']}

        Returns:
            Dictionary of query parameter names to lists of values
        """

        if self._query_params_multi_values is None:
            self._query_params_multi_values = {}
            if self.query_string:
                self._query_params_multi_values = urllib.parse.parse_qs(
                    self.query_string, keep_blank_values=True
                )
        return self._query_params_multi_values

    @property
    def query_string(self) -> str:
        """Raw query string as decoded string (e.g., 'page=1&limit=10')"""

        return self._scope.get("query_string", b"").decode("utf-8")

    @property
    def url(self) -> str:
        """Full URL as a string."""

        if self._url is None:
            scheme = self._scope.get("scheme", "http")
            host, port = self._scope.get("server", ("localhost", 80))

            self._url = f"{scheme}://{host}:{port}{self.path}"
            if self.query_string:
                self._url += f"?{self.query_string}"

        return self._url

    def _parse_form_data(self) -> None:
        """Parse URL-encoded form data from the request body."""

        if self._body:
            body_str = self._body.decode("utf-8")
            parsed = urllib.parse.parse_qs(body_str, keep_blank_values=True)
            self._form = {k: v[0] if v else "" for k, v in parsed.items()}

    async def _receive_complete_message(
        self,
        receive: Callable[[], Awaitable[Dict[str, Any]]],
    ) -> bytes:
        """
        Receive the complete HTTP request body from the ASGI receive callable.

        Handles cases where the body arrives in multiple parts (not to be confused with "content-type=multipart/form-data").
        """

        body_parts: List[bytes] = []
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body_part = message.get("body", b"")
                if body_part:
                    body_parts.append(body_part)
                if not message.get("more_body", False):
                    break
            elif message["type"] == "http.disconnect":
                break
        return b"".join(body_parts)

    def __del__(self):
        """
        Destructor to ensure cleanup happens even if not explicitly called.
        """
        try:
            self.cleanup_files()
        except Exception:
            # Silent cleanup in destructor
            pass

    def __repr__(self) -> str:
        return f"<Request {self.method} {self.path}>"
