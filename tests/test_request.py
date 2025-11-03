"""
Unit tests for Vira Request class.

"""

import pytest
from typing import Dict, Any, List, Optional

from vira.request import Request


def create_mock_receive(body=b"", more_body=False):
    """Helper to create mock receive callable for tests."""

    async def mock_receive():
        return {"type": "http.request", "body": body, "more_body": more_body}

    return mock_receive


def create_scope(
    method: str = "GET",
    path: str = "/",
    query_string: str = "",
    headers: Optional[Dict[str, str]] = None,
    server: tuple = ("localhost", 8000),
    scheme: str = "http",
    **kwargs,
) -> Dict[str, Any]:
    """
    Create a flexible ASGI scope for testing with full control over all parameters.
    """
    # Convert headers dict to ASGI format: List[List[bytes]]
    headers_list = []
    if headers:
        headers_list = [[k.encode(), v.encode()] for k, v in headers.items()]

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "query_string": (
            query_string.encode() if isinstance(query_string, str) else query_string
        ),
        "headers": headers_list,
        "server": server,
        "scheme": scheme,
    }
    scope.update(kwargs)  # Allow additional custom fields
    return scope


def create_multipart_body(
    boundary: str,
    form_data: Optional[Dict[str, str]] = None,
    files: Optional[List[Dict]] = None,
) -> bytes:
    """
    Create multipart/form-data body for testing file uploads.

    Args:
        boundary: Boundary string for multipart data
        form_data: Dict of form field names to values
        files: List of file dicts with keys: name, filename, content, content_type

    Returns:
        Complete multipart body as bytes
    """
    parts = []

    # Add form fields
    if form_data:
        for name, value in form_data.items():
            part = f"--{boundary}\r\n"
            part += f'Content-Disposition: form-data; name="{name}"\r\n'
            part += "\r\n"
            part += value
            part += "\r\n"
            parts.append(part.encode("utf-8"))

    # Add files
    if files:
        for file in files:
            part = f"--{boundary}\r\n"
            part += f'Content-Disposition: form-data; name="{file["name"]}"; filename="{file["filename"]}"\r\n'
            part += f'Content-Type: {file.get("content_type", "application/octet-stream")}\r\n'
            part += "\r\n"
            parts.append(part.encode("utf-8"))

            # Add file content
            content = file["content"]
            if isinstance(content, str):
                content = content.encode("utf-8")
            parts.append(content)

            # Add newline after content only if content is not empty or if it's the last file
            # This creates proper multipart formatting
            parts.append(b"\r\n")

    # Add closing boundary
    parts.append(f"--{boundary}--\r\n".encode("utf-8"))

    return b"".join(parts)


def create_multipart_headers(boundary: str) -> Dict[str, str]:
    """Create headers for multipart/form-data request."""
    return {"content-type": f"multipart/form-data; boundary={boundary}"}


class TestRequestInitialization:
    """Test Request initialization and factory methods."""

    def test_basic_initialization(self):
        """Test basic Request object initialization."""
        scope = create_scope()
        receive = create_mock_receive()

        request = Request(scope, receive)

        assert request._scope == scope
        assert request._receive == receive
        assert request._body is None
        assert request._form is None
        assert request._files is None

    def test_initialization_preserves_scope_data(self):
        """Test Request initialization preserves all scope data."""
        scope = create_scope(
            method="POST",
            path="/test",
            query_string="key=value",
            server=("example.com", 443),
            scheme="https",
        )
        receive = create_mock_receive()

        request = Request(scope, receive)

        assert request._scope == scope
        assert request._scope["method"] == "POST"
        assert request._scope["path"] == "/test"


class TestRequestBasicProperties:
    """Test basic Request properties."""

    def test_method_property(self):
        """Test method property returns scope method."""
        scope = create_scope(method="POST")
        request = Request(scope, create_mock_receive())

        assert request.method == "POST"

    def test_method_property_default(self):
        """Test method property returns GET when method is missing from scope."""
        # Create scope with missing method to test Request's default handling
        scope = {
            "type": "http",
            "path": "/",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
            "scheme": "http",
        }
        request = Request(scope, create_mock_receive())

        assert request.method == "GET"

    def test_path_property(self):
        """Test path property returns scope path."""
        scope = create_scope(path="/test/path")
        request = Request(scope, create_mock_receive())

        assert request.path == "/test/path"

    def test_path_property_default(self):
        """Test path property returns / when path is missing from scope."""
        # Create scope with missing path to test Request's default handling
        scope = {
            "type": "http",
            "method": "GET",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
            "scheme": "http",
        }
        request = Request(scope, create_mock_receive())

        assert request.path == "/"


class TestRequestHeaders:
    """Test Request headers functionality."""

    def test_headers_property_with_headers(self):
        """Test headers property with existing headers."""
        scope = create_scope(
            headers={
                "content-type": "application/json",
                "authorization": "Bearer token123",
            }
        )
        request = Request(scope, create_mock_receive())

        headers = request.headers
        assert headers["content-type"] == "application/json"
        assert headers["authorization"] == "Bearer token123"

    def test_headers_property_empty(self):
        """Test headers property with no headers."""
        scope = create_scope()
        request = Request(scope, create_mock_receive())

        headers = request.headers
        assert len(headers) == 0

    def test_headers_property_lowercase_access(self):
        """Test headers are accessible with lowercase keys."""
        scope = create_scope(headers={"Content-Type": "text/html"})
        request = Request(scope, create_mock_receive())

        headers = request.headers
        assert headers["content-type"] == "text/html"


class TestRequestQueryParameters:
    """Test Request query parameters functionality."""

    def test_query_params_property_with_params(self):
        """Test query_params property with existing parameters."""
        scope = create_scope(query_string="name=john&age=30&city=NYC")
        request = Request(scope, create_mock_receive())

        params = request.query_params
        assert params["name"] == "john"
        assert params["age"] == "30"
        assert params["city"] == "NYC"

    def test_query_params_property_empty(self):
        """Test query_params property with no parameters."""
        scope = create_scope()
        request = Request(scope, create_mock_receive())

        params = request.query_params
        assert len(params) == 0

    def test_query_params_property_duplicate_keys_first_wins(self):
        """Test query_params with duplicate parameter names returns first value."""
        scope = create_scope(query_string="tag=python&tag=web&tag=api")
        request = Request(scope, create_mock_receive())

        params = request.query_params
        # Implementation returns first value for duplicate keys
        assert params["tag"] == "python"

    def test_query_params_multi_values_property_duplicate_keys(self):
        """Test query_params_multi_values with duplicate parameter names returns a list of values."""
        scope = create_scope(query_string="tag=python&tag=web&tag=api")
        request = Request(scope, create_mock_receive())

        params = request.query_params_multi_values
        # Implementation returns first value for duplicate keys
        assert params["tag"] == ["python", "web", "api"]

    def test_query_params_property_url_encoded(self):
        """Test query_params with URL-encoded values."""
        scope = create_scope(query_string="message=hello%20world&symbol=%26")
        request = Request(scope, create_mock_receive())

        params = request.query_params
        assert params["message"] == "hello world"
        assert params["symbol"] == "&"


class TestRequestCookies:
    """Test Request cookies functionality."""

    def test_cookies_property_with_cookies(self):
        """Test cookies property with existing cookies."""
        scope = create_scope(
            headers={"cookie": "session_id=abc123; user_pref=dark_mode"}
        )
        request = Request(scope, create_mock_receive())

        cookies = request.cookies
        assert cookies["session_id"] == "abc123"
        assert cookies["user_pref"] == "dark_mode"

    def test_cookies_property_empty(self):
        """Test cookies property with no cookies."""
        scope = create_scope(headers={"cookie": ""})
        request = Request(scope, create_mock_receive())

        cookies = request.cookies
        assert len(cookies) == 0

    def test_cookies_property_no_cookie_header(self):
        """Test cookies property when no cookie header exists."""
        scope = create_scope()
        request = Request(scope, create_mock_receive())

        cookies = request.cookies
        assert len(cookies) == 0

    def test_cookies_property_raw_values(self):
        """Test cookies with URL-encoded values remain encoded."""
        scope = create_scope(
            headers={"cookie": "data=%7B%22key%22%3A%22value%22%7D; simple=test"}
        )
        request = Request(scope, create_mock_receive())

        cookies = request.cookies
        # Implementation doesn't automatically URL decode
        assert cookies["data"] == "%7B%22key%22%3A%22value%22%7D"
        assert cookies["simple"] == "test"


class TestRequestBodyProcessing:
    """Test Request body processing functionality."""

    @pytest.mark.asyncio
    async def test_load_body_success(self):
        """Test successful body loading."""
        scope = create_scope()
        receive = create_mock_receive(body=b"test body content")
        request = Request(scope, receive)

        await request.load_body()

        assert request._body == b"test body content"

    @pytest.mark.asyncio
    async def test_load_body_empty(self):
        """Test loading empty body."""
        scope = create_scope()
        receive = create_mock_receive(body=b"")
        request = Request(scope, receive)

        await request.load_body()

        assert request._body == b""

    @pytest.mark.asyncio
    async def test_load_body_already_loaded(self):
        """Test loading body when already loaded."""
        scope = create_scope()
        receive = create_mock_receive(body=b"original content")
        request = Request(scope, receive)

        await request.load_body()
        # Modify the receive to return different content
        request._receive = create_mock_receive(body=b"new content")
        await request.load_body()

        # Should still have original content
        assert request._body == b"original content"

    def test_body_property_access_without_loading(self):
        """Test body method access without loading raises error."""
        scope = create_scope()
        receive = create_mock_receive(body=b"content")
        request = Request(scope, receive)

        # Should raise error if body not loaded
        with pytest.raises(RuntimeError, match="Request body has not been loaded"):
            _ = request.body()


class TestRequestFormData:
    """Test Request form data functionality."""

    @pytest.mark.asyncio
    async def test_form_property_urlencoded(self):
        """Test form property with URL-encoded data."""
        scope = create_scope(
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        form_data = "name=John+Doe&email=john%40example.com&age=30"
        receive = create_mock_receive(body=form_data.encode())
        request = Request(scope, receive)

        await request.load_body()  # Need to load body first
        form = request.form  # Property, not method

        assert form["name"] == "John Doe"
        assert form["email"] == "john@example.com"
        assert form["age"] == "30"

    @pytest.mark.asyncio
    async def test_form_property_empty(self):
        """Test form property with empty data."""
        scope = create_scope(
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        receive = create_mock_receive(body=b"")
        request = Request(scope, receive)

        await request.load_body()
        form = request.form

        assert len(form) == 0

    @pytest.mark.asyncio
    async def test_form_property_not_form_data(self):
        """Test form property with non-form content type."""
        scope = create_scope(headers={"content-type": "application/json"})
        receive = create_mock_receive(body=b'{"key": "value"}')
        request = Request(scope, receive)

        await request.load_body()
        form = request.form

        # Should return empty form for non-form content
        assert len(form) == 0


class TestRequestContentTypeHelpers:
    """Test Request content type helper methods."""

    def test_is_json_true(self):
        """Test is_json returns True for JSON content type."""
        scope = create_scope(headers={"content-type": "application/json"})
        request = Request(scope, create_mock_receive())

        assert request.is_json() is True

    def test_is_json_false(self):
        """Test is_json returns False for non-JSON content type."""
        scope = create_scope(headers={"content-type": "text/html"})
        request = Request(scope, create_mock_receive())

        assert request.is_json() is False

    def test_is_json_no_content_type(self):
        """Test is_json returns False when no content type."""
        scope = create_scope()
        request = Request(scope, create_mock_receive())

        assert request.is_json() is False

    def test_is_form_true(self):
        """Test is_form returns True for form-urlencoded content type."""
        scope = create_scope(
            headers={"content-type": "application/x-www-form-urlencoded"}
        )
        request = Request(scope, create_mock_receive())

        assert request.is_form() is True

    def test_is_form_false(self):
        """Test is_form returns False for non-form content type."""
        scope = create_scope(headers={"content-type": "application/json"})
        request = Request(scope, create_mock_receive())

        assert request.is_form() is False


class TestRequestURL:
    """Test Request URL construction and properties."""

    def test_url_construction_basic(self):
        """Test basic URL construction."""
        scope = create_scope(
            scheme="http", server=("localhost", 8000), path="/api/users"
        )
        request = Request(scope, create_mock_receive())

        url = request.url
        assert str(url) == "http://localhost:8000/api/users"

    def test_url_construction_with_query_includes_port(self):
        """Test URL construction with query string includes port."""
        scope = create_scope(
            scheme="https",
            server=("api.example.com", 443),
            path="/search",
            query_string="q=python&limit=10",
        )
        request = Request(scope, create_mock_receive())

        url = request.url
        # Implementation includes port even for default HTTPS
        assert "api.example.com:443" in str(url)
        assert "q=python&limit=10" in str(url)

    def test_url_construction_custom_port(self):
        """Test URL construction with custom port."""
        scope = create_scope(scheme="http", server=("localhost", 3000), path="/api")
        request = Request(scope, create_mock_receive())

        url = request.url
        assert str(url) == "http://localhost:3000/api"

    def test_url_construction_no_server(self):
        """Test URL construction when server info missing from scope."""
        # Create scope with missing server to test Request's default handling
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "scheme": "http",
        }
        request = Request(scope, create_mock_receive())

        url = request.url
        # Should use defaults
        assert "localhost" in str(url)
        assert "/test" in str(url)


class TestRequestFileHandling:
    """Test Request file handling and multipart form data functionality."""

    @pytest.mark.asyncio
    async def test_single_file_upload(self):
        """Test uploading a single file via multipart form data."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = b"Hello, this is test file content!"

        body = create_multipart_body(
            boundary=boundary,
            files=[
                {
                    "name": "upload_file",
                    "filename": "test.txt",
                    "content": file_content,
                    "content_type": "text/plain",
                }
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        # Check files property
        files = request.files
        assert len(files) == 1

        uploaded_file = files[0]
        assert uploaded_file.filename == "test.txt"
        assert uploaded_file.content_type == "text/plain"
        assert uploaded_file.size == len(file_content)

        # Test file content access
        with uploaded_file.open() as f:
            assert f.read() == file_content

    @pytest.mark.asyncio
    async def test_multiple_files_upload(self):
        """Test uploading multiple files via multipart form data."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

        file1_content = b"Content of first file"
        file2_content = b"Content of second file"

        body = create_multipart_body(
            boundary=boundary,
            files=[
                {
                    "name": "file1",
                    "filename": "document.txt",
                    "content": file1_content,
                    "content_type": "text/plain",
                },
                {
                    "name": "file2",
                    "filename": "image.png",
                    "content": file2_content,
                    "content_type": "image/png",
                },
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        # Check files property
        files = request.files
        assert len(files) == 2

        # Verify first file
        file1 = files[0]
        assert file1.filename == "document.txt"
        assert file1.content_type == "text/plain"
        assert file1.size == len(file1_content)

        # Verify second file
        file2 = files[1]
        assert file2.filename == "image.png"
        assert file2.content_type == "image/png"
        assert file2.size == len(file2_content)

        # Test file content access
        with file1.open() as f:
            assert f.read() == file1_content
        with file2.open() as f:
            assert f.read() == file2_content

    @pytest.mark.asyncio
    async def test_mixed_form_data_and_files(self):
        """Test form data with both regular fields and file uploads."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = b"File content for mixed upload test"

        body = create_multipart_body(
            boundary=boundary,
            form_data={
                "username": "testuser",
                "description": "File upload with description",
                "category": "documents",
            },
            files=[
                {
                    "name": "document",
                    "filename": "report.pdf",
                    "content": file_content,
                    "content_type": "application/pdf",
                }
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        # Check form data
        form = request.form
        assert form["username"] == "testuser"
        assert form["description"] == "File upload with description"
        assert form["category"] == "documents"

        # Check files
        files = request.files
        assert len(files) == 1

        uploaded_file = files[0]
        assert uploaded_file.filename == "report.pdf"
        assert uploaded_file.content_type == "application/pdf"
        assert uploaded_file.size == len(file_content)

        with uploaded_file.open() as f:
            assert f.read() == file_content

    @pytest.mark.asyncio
    async def test_file_upload_with_special_characters(self):
        """Test file upload with special characters in filename and content."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = "Special content: éñ中文🚀\nNew line content".encode("utf-8")

        body = create_multipart_body(
            boundary=boundary,
            files=[
                {
                    "name": "special_file",
                    "filename": "special-file名前.txt",
                    "content": file_content,
                    "content_type": "text/plain; charset=utf-8",
                }
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        files = request.files
        assert len(files) == 1

        uploaded_file = files[0]
        assert uploaded_file.filename == "special-file名前.txt"
        assert uploaded_file.content_type == "text/plain; charset=utf-8"
        assert uploaded_file.size == len(file_content)

        with uploaded_file.open() as f:
            assert f.read() == file_content

    @pytest.mark.asyncio
    async def test_binary_file_upload(self):
        """Test uploading binary file content."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        # Create some binary content
        binary_content = bytes(range(256))  # All byte values 0-255

        body = create_multipart_body(
            boundary=boundary,
            files=[
                {
                    "name": "binary_file",
                    "filename": "data.bin",
                    "content": binary_content,
                    "content_type": "application/octet-stream",
                }
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        files = request.files
        assert len(files) == 1

        uploaded_file = files[0]
        assert uploaded_file.filename == "data.bin"
        assert uploaded_file.content_type == "application/octet-stream"
        assert uploaded_file.size == len(binary_content)

        with uploaded_file.open() as f:
            assert f.read() == binary_content

    @pytest.mark.asyncio
    async def test_empty_file_upload(self):
        """Test uploading an empty file."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

        body = create_multipart_body(
            boundary=boundary,
            files=[
                {
                    "name": "empty_file",
                    "filename": "empty.txt",
                    "content": b"",
                    "content_type": "text/plain",
                }
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        files = request.files
        assert len(files) == 1

        uploaded_file = files[0]
        assert uploaded_file.filename == "empty.txt"
        assert uploaded_file.size == 0

        with uploaded_file.open() as f:
            assert f.read() == b""

    @pytest.mark.asyncio
    async def test_file_upload_missing_boundary(self):
        """Test multipart request with missing boundary."""
        scope = create_scope(
            method="POST",
            headers={"content-type": "multipart/form-data"},  # No boundary
        )
        receive = create_mock_receive(body=b"some content")
        request = Request(scope, receive)

        await request.load_body()

        # Should handle gracefully with empty files and form
        assert request.files == []
        assert request.form == {}

    @pytest.mark.asyncio
    async def test_malformed_multipart_data(self):
        """Test handling of malformed multipart data."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        # Create malformed multipart data (missing proper structure)
        malformed_body = (
            b"--" + boundary.encode() + b"\r\nmalformed content without proper headers"
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=malformed_body)
        request = Request(scope, receive)

        await request.load_body()

        # Should handle gracefully
        assert request.files == []
        assert request.form == {}

    def test_files_property_empty_non_multipart(self):
        """Test files property returns empty list for non-multipart."""
        scope = create_scope(headers={"content-type": "application/json"})
        request = Request(scope, create_mock_receive())

        files = request.files  # Property, not method

        assert files == []

    @pytest.mark.asyncio
    async def test_file_cleanup_functionality(self):
        """Test file cleanup removes temporary files."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        file_content = b"Content for cleanup test"

        body = create_multipart_body(
            boundary=boundary,
            files=[
                {
                    "name": "test_file",
                    "filename": "cleanup_test.txt",
                    "content": file_content,
                    "content_type": "text/plain",
                }
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        files = request.files
        assert len(files) == 1

        uploaded_file = files[0]
        temp_path = uploaded_file._temp_path

        # Verify file exists before cleanup
        import os

        assert os.path.exists(temp_path)

        # Cleanup files
        request.cleanup_files()

        # File should be removed after cleanup
        assert not os.path.exists(temp_path)

    @pytest.mark.asyncio
    async def test_file_with_legitimate_trailing_newlines(self):
        """Test that files with legitimate trailing newlines preserve them."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

        # File content that legitimately ends with newlines (like a text file)
        file_content = b"Line 1\nLine 2\nLine 3\r\n\r\n"  # File ends with two newlines

        body = create_multipart_body(
            boundary=boundary,
            files=[
                {
                    "name": "text_file",
                    "filename": "document.txt",
                    "content": file_content,
                    "content_type": "text/plain",
                }
            ],
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        files = request.files
        assert len(files) == 1

        uploaded_file = files[0]
        assert uploaded_file.filename == "document.txt"

        # Verify the file content preserves legitimate trailing newlines
        with uploaded_file.open() as f:
            read_content = f.read()
            assert read_content == file_content
            # Specifically check that the legitimate trailing newlines are preserved
            assert read_content.endswith(b"\r\n\r\n")

    @pytest.mark.asyncio
    async def test_form_field_with_legitimate_trailing_newlines(self):
        """Test that form fields with legitimate trailing newlines preserve them."""
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"

        # Form field content that legitimately ends with newlines
        field_value = "Line 1\nLine 2\nLine 3\n\n"  # Field ends with two newlines

        body = create_multipart_body(
            boundary=boundary, form_data={"message": field_value}
        )

        scope = create_scope(method="POST", headers=create_multipart_headers(boundary))
        receive = create_mock_receive(body=body)
        request = Request(scope, receive)

        await request.load_body()

        form_data = request.form
        assert "message" in form_data

        # Verify the form field preserves legitimate trailing newlines
        retrieved_value = form_data["message"]
        assert retrieved_value == field_value
        # Specifically check that the legitimate trailing newlines are preserved
        assert retrieved_value.endswith("\n\n")


class TestRequestCleanup:
    """Test Request cleanup functionality."""

    def test_cleanup_files_no_files(self):
        """Test cleanup_files when no files are present."""
        scope = create_scope()
        request = Request(scope, create_mock_receive())

        # Should not raise any errors
        request.cleanup_files()

    def test_cleanup_all_active_requests_smoke_test(self):
        """Test cleanup_all_active_requests returns count."""
        # This is a smoke test since the method is mostly for cleanup
        count = Request.cleanup_all_active_requests()
        assert isinstance(count, int)
        assert count >= 0


class TestRequestStringRepresentation:
    """Test Request string representation - simple wrapper test."""

    def test_repr_method(self):
        """Test __repr__ method shows method and path."""
        scope = create_scope(method="POST", path="/api/users")
        request = Request(scope, create_mock_receive())

        assert repr(request) == "<Request POST /api/users>"

    def test_repr_method_defaults(self):
        """Test __repr__ with default values."""
        scope = {"type": "http"}  # Missing method and path
        request = Request(scope, create_mock_receive())

        assert repr(request) == "<Request GET />"


if __name__ == "__main__":
    print("Running focused Vira Request unit tests...")
    print("Use: pytest test_request_fixed.py -v for detailed output")
