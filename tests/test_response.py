"""
Focused unit tests for Vira Response class.

Each test method verifies exactly one specific behavior to follow the Single Responsibility Principle.
"""

import json
import pytest
from datetime import datetime
from vira.response import (
    Response,
    text_response,
    html_response,
    json_response,
    redirect_response,
)
from vira.status import HTTPStatus


class TestResponseInitialization:
    """Test Response initialization behaviors."""

    def test_default_initialization(self):
        """Test Response default initialization values."""
        response = Response()
        assert response.status_code == 200
        assert response.headers == {"content-type": "text/plain; charset=utf-8"}
        assert response.body == b""
        assert response._cookies == []

    def test_initialization_with_custom_headers(self):
        """Test Response initialization with custom headers."""
        headers = {"X-Custom": "value", "X-API-Version": "2.0"}
        response = Response("Hello", headers=headers)
        assert response.headers["X-Custom"] == "value"
        assert response.headers["X-API-Version"] == "2.0"
        assert "content-type" in response.headers

    def test_initialization_with_explicit_content_type(self):
        """Test Response initialization with explicit content type override."""
        response = Response("Hello", content_type="application/custom")
        assert response.headers["content-type"] == "application/custom"


class TestResponseContentDetection:
    """Test automatic content type detection for different content types."""

    def test_string_content_detection(self):
        """Test string content auto-detection."""
        response = Response("Hello World")
        assert response.body == b"Hello World"
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_html_content_detection_with_doctype(self):
        """Test HTML content detection with DOCTYPE."""
        response = Response("<!DOCTYPE html><html></html>")
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_html_content_detection_with_tags(self):
        """Test HTML content detection with HTML tags."""
        response = Response("<h1>Title</h1>")
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_json_dict_content_detection(self):
        """Test JSON content detection with dictionary."""
        data = {"key": "value", "users": [{"id": 1, "name": "John"}]}
        response = Response(data)
        assert response.headers["content-type"] == "application/json; charset=utf-8"
        assert json.loads(response.body.decode()) == data

    def test_json_list_content_detection(self):
        """Test JSON content detection with list."""
        data = [1, 2, 3]
        response = Response(data)
        assert response.headers["content-type"] == "application/json; charset=utf-8"
        assert response.body == b"[1, 2, 3]"

    def test_bytes_content_handling(self):
        """Test bytes content handling."""
        binary_data = b"Binary data"
        response = Response(binary_data)
        assert response.body == binary_data
        assert response.headers["content-type"] == "application/octet-stream"

    def test_integer_content_handling(self):
        """Test integer content handling."""
        response = Response(42)
        assert response.body == b"42"
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_float_content_handling(self):
        """Test float content handling."""
        response = Response(3.14)
        assert response.body == b"3.14"
        assert response.headers["content-type"] == "text/plain; charset=utf-8"


class TestResponseHeaderOperations:
    """Test individual header operations."""

    def test_set_header_basic(self):
        """Test basic header setting."""
        response = Response("Hello")
        response.set_header("X-Custom", "test-value")
        assert response.headers["X-Custom"] == "test-value"

    def test_set_header_overwrites_existing(self):
        """Test that set_header overwrites existing headers."""
        response = Response("Hello")
        response.set_header("X-Test", "initial")
        response.set_header("X-Test", "updated")
        assert response.headers["X-Test"] == "updated"

    def test_set_header_method_chaining(self):
        """Test header setting with method chaining."""
        response = (
            Response("Hello")
            .set_header("X-First", "value1")
            .set_header("X-Second", "value2")
            .set_header("X-Third", "value3")
        )
        assert response.headers["X-First"] == "value1"
        assert response.headers["X-Second"] == "value2"
        assert response.headers["X-Third"] == "value3"


class TestResponseCookieOperations:
    """Test individual cookie operations."""

    def test_set_cookie_basic(self):
        """Test basic cookie setting."""
        response = Response("Hello")
        response.set_cookie("session", "abc123")
        assert len(response._cookies) == 1
        assert "session=abc123; Path=/" in response._cookies[0]

    def test_set_cookie_with_all_attributes(self):
        """Test cookie setting with all attributes combined."""
        response = Response("Hello")
        expires = datetime(2025, 6, 15, 12, 0, 0)
        response.set_cookie(
            "full_cookie",
            "complete_value",
            max_age=7200,
            expires=expires,
            path="/api",
            domain="api.example.com",
            secure=True,
            httponly=True,
            samesite="Lax",
        )
        cookie = response._cookies[0]
        assert (
            "full_cookie=complete_value" in cookie
        ), "Cookie name and value not set correctly"
        assert "Max-Age=7200" in cookie, "Max-Age attribute missing or incorrect"
        assert (
            "Expires=Sun, 15 Jun 2025 12:00:00 GMT" in cookie
        ), "Expires attribute missing or incorrect"
        assert "Path=/api" in cookie, "Path attribute missing or incorrect"
        assert (
            "Domain=api.example.com" in cookie
        ), "Domain attribute missing or incorrect"
        assert "Secure" in cookie, "Secure attribute missing"
        assert "HttpOnly" in cookie, "HttpOnly attribute missing"
        assert "SameSite=Lax" in cookie, "SameSite attribute missing or incorrect"

    def test_set_multiple_cookies(self):
        """Test setting multiple cookies."""
        response = Response("Hello")
        response.set_cookie("session", "abc123")
        response.set_cookie("user_id", "456", max_age=1800)
        assert len(response._cookies) == 2

    def test_delete_cookie(self):
        """Test cookie deletion."""
        response = Response("Hello")

        response.delete_cookie("old_session", path="/admin", domain="example.com")
        delete_cookie = response._cookies[0]
        assert "old_session=" in delete_cookie
        assert "Max-Age=0" in delete_cookie
        assert "Path=/admin" in delete_cookie
        assert "Domain=example.com" in delete_cookie

    def test_clear_cookies(self):
        """Test clearing all cookies."""
        response = Response("Hello")
        response.set_cookie("temp1", "value1")
        response.set_cookie("temp2", "value2")
        response.clear_cookies()
        assert len(response._cookies) == 0

    def test_cookie_method_chaining(self):
        """Test cookie operations with method chaining."""
        response = (
            Response("Hello")
            .set_cookie("session", "abc123")
            .set_cookie("user", "john", max_age=3600)
            .delete_cookie("old_token")
        )
        assert len(response._cookies) == 3


class TestResponseASGIConversion:
    """Test ASGI response conversion."""

    def test_basic_asgi_conversion(self):
        """Test basic ASGI response conversion."""
        response = Response("Hello World", status_code=200)
        asgi = response.to_asgi_response()
        assert asgi["status"] == 200
        assert asgi["body"] == b"Hello World"
        assert isinstance(asgi["headers"], list)

    def test_asgi_headers_format(self):
        """Test ASGI headers format conversion."""
        response = Response("Hello")
        asgi = response.to_asgi_response()
        content_type_header = next(
            (h for h in asgi["headers"] if h[0] == b"content-type"), None
        )
        assert content_type_header is not None
        assert content_type_header[1] == b"text/plain; charset=utf-8"

    def test_asgi_custom_headers_conversion(self):
        """Test ASGI conversion with custom headers."""
        headers = {"X-Custom": "value", "X-API-Version": "2.0"}
        response = Response("Test", headers=headers)
        asgi = response.to_asgi_response()
        headers_dict = {h[0].decode(): h[1].decode() for h in asgi["headers"]}
        assert headers_dict["x-custom"] == "value"
        assert headers_dict["x-api-version"] == "2.0"

    def test_asgi_cookies_conversion(self):
        """Test ASGI conversion with cookies."""
        response = Response("Hello")
        response.set_cookie("session", "abc123")
        response.set_cookie("user", "john", max_age=3600)
        asgi = response.to_asgi_response()
        cookie_headers = [h for h in asgi["headers"] if h[0] == b"set-cookie"]
        assert len(cookie_headers) == 2

    def test_asgi_json_content_conversion(self):
        """Test ASGI conversion with JSON content."""
        data = {"message": "success", "data": [1, 2, 3]}
        response = Response(data, status_code=HTTPStatus.HTTP_201_CREATED)
        asgi = response.to_asgi_response()
        assert asgi["status"] == 201
        assert json.loads(asgi["body"].decode()) == data


class TestResponseStringRepresentation:
    """Test Response string representation."""

    def test_repr_default_status(self):
        """Test __repr__ with default status."""
        response = Response("Hello")
        assert repr(response) == "<Response 200>"

    def test_repr_custom_status(self):
        """Test __repr__ with custom status."""
        response = Response("Not Found", status_code=404)
        assert repr(response) == "<Response 404>"

    def test_repr_httpstatus_enum(self):
        """Test __repr__ with HTTPStatus enum."""
        response = Response("Created", status_code=HTTPStatus.HTTP_201_CREATED)
        assert repr(response) == "<Response 201>"


class TestConvenienceFunctions:
    """Test convenience response functions - minimal smoke tests since they're just Response wrappers."""

    def test_text_response_smoke_test(self):
        """Test text_response returns Response with correct content type."""
        response = text_response("Plain text content")
        assert isinstance(response, Response)
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_html_response_smoke_test(self):
        """Test html_response returns Response with correct content type."""
        response = html_response("<h1>Hello World</h1>")
        assert isinstance(response, Response)
        assert response.headers["content-type"] == "text/html; charset=utf-8"

    def test_json_response_smoke_test(self):
        """Test json_response returns Response with correct content type."""
        response = json_response({"key": "value"})
        assert isinstance(response, Response)
        assert response.headers["content-type"] == "application/json; charset=utf-8"

    def test_redirect_response_smoke_test(self):
        """Test redirect_response returns Response with location header."""
        response = redirect_response("https://example.com")
        assert isinstance(response, Response)
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com"


class TestResponseUnicodeHandling:
    """Test Response Unicode content handling."""

    def test_unicode_string_content(self):
        """Test Unicode string content handling."""
        unicode_content = "Hello 世界 🌍"
        response = Response(unicode_content)
        assert response.body == unicode_content.encode("utf-8")
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_unicode_json_content(self):
        """Test Unicode JSON content handling."""
        unicode_data = {"message": "Hello 世界", "emoji": "🎉"}
        response = Response(unicode_data)
        decoded_data = json.loads(response.body.decode("utf-8"))
        assert decoded_data == unicode_data


class TestResponseEdgeCases:
    """Test Response edge cases."""

    def test_empty_string_content(self):
        """Test empty string content handling."""
        response = Response("")
        assert response.body == b""
        assert response.headers["content-type"] == "text/plain; charset=utf-8"

    def test_boolean_false_content(self):
        """Test False boolean content handling."""
        response = Response(False)
        assert response.body == b"False"

    def test_boolean_true_content(self):
        """Test True boolean content handling."""
        response = Response(True)
        assert response.body == b"True"

    def test_empty_cookie_value(self):
        """Test cookie with empty value."""
        response = Response("Hello")
        response.set_cookie("empty", "")
        assert "empty=; Path=/" in response._cookies[0]

    def test_cookie_value_with_spaces(self):
        """Test cookie value with spaces."""
        response = Response("Hello")
        response.set_cookie("spaces", "value with spaces")
        assert "spaces=value with spaces; Path=/" in response._cookies[0]

    def test_header_value_with_spaces(self):
        """Test header value with spaces."""
        response = Response("Hello")
        response.set_header("X-Special", "value with spaces")
        assert response.headers["X-Special"] == "value with spaces"


if __name__ == "__main__":
    print("Running focused Vira Response unit tests...")
    print("Use: pytest test_response.py -v for detailed output")
