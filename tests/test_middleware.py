"""
Test suite for virapi middleware system.

This module tests the middleware framework including:
- MiddlewareChain functionality
- Built-in middleware (CORS, Exception)
- Middleware execution order and interaction
- Custom middleware creation and integration
"""

import pytest
from typing import Callable, Awaitable
from virapi import virapi, Request, Response, text_response, json_response
from virapi.testing import TestClient, TestRequest
from virapi.middleware import MiddlewareChain
from virapi.middleware.builtin_middleware import (
    CORSMiddleware,
    ExceptionMiddleware,
)


class TestMiddlewareChain:
    """Test the MiddlewareChain class."""

    def test_middleware_chain_creation(self):
        """Test creating an empty middleware chain."""
        chain = MiddlewareChain()
        assert chain.count() == 0

    def test_middleware_chain_add(self):
        """Test adding middleware to the chain."""
        chain = MiddlewareChain()

        async def middleware1(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            return await call_next(request)

        async def middleware2(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            return await call_next(request)

        chain.add(middleware1)
        assert chain.count() == 1

        chain.add(middleware2)
        assert chain.count() == 2

    def test_middleware_chain_clear(self):
        """Test clearing all middleware from the chain."""
        chain = MiddlewareChain()

        async def middleware(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            return await call_next(request)

        chain.add(middleware)
        assert chain.count() == 1

        chain.clear()
        assert chain.count() == 0

    @pytest.mark.asyncio
    async def test_middleware_chain_build_empty(self):
        """Test building chain with no middleware returns original endpoint."""
        chain = MiddlewareChain()

        async def endpoint(request: Request):
            return text_response("endpoint")

        handler = chain.build(endpoint)
        assert handler == endpoint

    @pytest.mark.asyncio
    async def test_middleware_chain_execution_order(self):
        """Test that middleware execute in correct order."""
        chain = MiddlewareChain()
        execution_order = []

        async def middleware1(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            execution_order.append("middleware1_before")
            response = await call_next(request)
            execution_order.append("middleware1_after")
            return response

        async def middleware2(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            execution_order.append("middleware2_before")
            response = await call_next(request)
            execution_order.append("middleware2_after")
            return response

        async def endpoint(request: Request):
            execution_order.append("endpoint")
            return text_response("test")

        chain.add(middleware1)
        chain.add(middleware2)

        handler = chain.build(endpoint)

        # Create a mock request
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/",
            "query_string": b"",
            "headers": [],
        }

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request(scope, mock_receive)
        await request.load_body()

        response = await handler(request)

        # Verify execution order: middleware1 -> middleware2 -> endpoint -> middleware2 -> middleware1
        expected_order = [
            "middleware1_before",
            "middleware2_before",
            "endpoint",
            "middleware2_after",
            "middleware1_after",
        ]
        assert execution_order == expected_order
        assert response.body == b"test"


class TestCustomMiddleware:
    """Test custom middleware creation and behavior."""

    def test_custom_middleware(self):
        """Test custom middleware integrated into virapi app."""
        app = virapi()

        # Custom middleware that adds a header
        async def add_header_middleware(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            response = await call_next(request)
            response.headers["X-Custom-Header"] = "middleware-added"
            return response

        # Custom middleware that modifies the request
        async def modify_request_middleware(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            # Add custom attribute to request using setattr
            setattr(request, "custom_data", "modified-by-middleware")
            return await call_next(request)

        app.add_middleware(add_header_middleware)
        app.add_middleware(modify_request_middleware)

        @app.get("/test")
        async def test_handler(request: Request):
            custom_data = getattr(request, "custom_data", "not-set")
            return json_response({"custom_data": custom_data})

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert (
            response.headers.get("x-custom-header") == "middleware-added"
        )  # Headers are lowercase
        data = response.json()
        assert data["custom_data"] == "modified-by-middleware"

    def test_middleware_short_circuit(self):
        """Test middleware that short-circuits the chain."""
        app = virapi()

        # Middleware that returns early without calling next
        async def auth_middleware(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            auth_header = request.headers.get("authorization")
            if not auth_header:
                return json_response({"error": "Unauthorized"}, status_code=401)
            return await call_next(request)

        app.add_middleware(auth_middleware)

        @app.get("/protected")
        async def protected_handler(request: Request):
            return json_response({"message": "Access granted"})

        client = TestClient(app)

        # Request without authorization header
        response = client.get("/protected")
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "Unauthorized"

        # Request with authorization header
        test_request = TestRequest().set_headers(authorization="Bearer token123")
        response = client.get("/protected", test_request)
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Access granted"


class TestExceptionMiddleware:
    """Test the ExceptionMiddleware."""

    def test_exception_middleware_production_mode(self):
        """Test exception middleware in production mode."""
        app = virapi()
        app.add_middleware(ExceptionMiddleware(mode="production"))

        @app.get("/error")
        async def error_handler(request: Request):
            raise ValueError("Something went wrong")

        client = TestClient(app)
        response = client.get("/error")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "HTTP_500_INTERNAL_SERVER_ERROR"
        assert data["error"]["message"] == "Internal Server Error"
        # Should not contain detailed error information in production
        assert "traceback" not in data["error"]

    def test_exception_middleware_debug_mode(self):
        """Test exception middleware in debug mode."""
        app = virapi()
        app.add_middleware(ExceptionMiddleware(mode="debug"))

        @app.get("/error")
        async def error_handler(request: Request):
            raise ValueError("Something went wrong")

        client = TestClient(app)
        response = client.get("/error")

        assert response.status_code == 500
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "ValueError"
        assert data["error"]["message"] == "Something went wrong"
        assert "detail" in data["error"]
        assert "traceback" in data["error"]
        assert "ValueError" in data["error"]["traceback"]

    def test_exception_middleware_no_exception(self):
        """Test that exception middleware doesn't interfere with normal responses."""
        app = virapi()
        app.add_middleware(ExceptionMiddleware(mode="debug"))

        @app.get("/normal")
        async def normal_handler(request: Request):
            return json_response({"status": "ok"})

        client = TestClient(app)
        response = client.get("/normal")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"


class TestCORSMiddleware:
    """Test the CORSMiddleware."""

    def test_cors_middleware_basic(self):
        """Test basic CORS functionality."""
        app = virapi()
        app.add_middleware(
            CORSMiddleware(
                allow_origins=["http://localhost:3000"],
                allow_methods=["GET", "POST"],
                allow_headers=["content-type"],
            )
        )

        @app.get("/api/test")
        async def test_handler(request: Request):
            return json_response({"message": "test"})

        client = TestClient(app)

        # Test simple GET request
        response = client.get("/api/test")
        assert response.status_code == 200

        # Test preflight OPTIONS request
        test_request = TestRequest().set_headers(
            origin="http://localhost:3000",
            **{
                "access-control-request-method": "POST",
                "access-control-request-headers": "content-type",
            }
        )
        response = client.options("/api/test", test_request)
        assert response.status_code == 204  # OPTIONS requests return 204
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_cors_middleware_wildcard_origin(self):
        """Test CORS with wildcard origin."""
        app = virapi()
        app.add_middleware(CORSMiddleware(allow_origins=["*"]))

        @app.get("/api/test")
        async def test_handler(request: Request):
            return json_response({"message": "test"})

        client = TestClient(app)
        test_request = TestRequest().set_headers(origin="http://example.com")
        response = client.get("/api/test", test_request)

        assert response.status_code == 200
        # When wildcard is used, the middleware should reflect the requesting origin
        assert (
            response.headers.get("access-control-allow-origin") == "http://example.com"
        )

    def test_cors_middleware_credentials(self):
        """Test CORS with credentials."""
        app = virapi()
        app.add_middleware(
            CORSMiddleware(
                allow_origins=["http://localhost:3000"],
                allow_credentials=True,
            )
        )

        @app.get("/api/test")
        async def test_handler(request: Request):
            return json_response({"message": "test"})

        client = TestClient(app)
        test_request = TestRequest().set_headers(origin="http://localhost:3000")
        response = client.get("/api/test", test_request)

        assert response.status_code == 200
        assert response.headers.get("access-control-allow-credentials") == "true"


class TestMiddlewareIntegration:
    """Test multiple middleware working together."""

    def test_multiple_middleware_order(self):
        """Test that multiple middleware execute in correct order."""
        app = virapi()

        # Add middleware in order: Exception -> CORS -> Custom
        app.add_middleware(ExceptionMiddleware(mode="debug"))
        app.add_middleware(CORSMiddleware(allow_origins=["*"]))

        # Custom middleware that adds execution tracking
        async def tracking_middleware(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            response = await call_next(request)
            response.headers["X-Tracking"] = "processed"
            return response

        app.add_middleware(tracking_middleware)

        @app.get("/test")
        async def test_handler(request: Request):
            return json_response({"message": "success"})

        client = TestClient(app)
        test_request = TestRequest().set_headers(origin="http://localhost:3000")
        response = client.get("/test", test_request)

        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
        assert response.headers.get("x-tracking") == "processed"

    def test_middleware_exception_handling(self):
        """Test that exception middleware catches errors from other middleware."""
        app = virapi()

        # Add exception middleware first
        app.add_middleware(ExceptionMiddleware(mode="debug"))

        # Add failing middleware
        async def failing_middleware(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            if request.path == "/fail":
                raise RuntimeError("Middleware failed")
            return await call_next(request)

        app.add_middleware(failing_middleware)

        @app.get("/fail")
        async def fail_handler(request: Request):
            return text_response("should not reach here")

        @app.get("/success")
        async def success_handler(request: Request):
            return text_response("success")

        client = TestClient(app)

        # Test failing middleware
        response = client.get("/fail")
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["type"] == "RuntimeError"
        assert "Middleware failed" in data["error"]["message"]

        # Test successful request
        response = client.get("/success")
        assert response.status_code == 200
        assert response.text() == "success"

    def test_middleware_with_path_parameters(self):
        """Test that middleware works correctly with path parameters."""
        app = virapi()

        # Middleware that logs the request path
        async def logging_middleware(
            request: Request, call_next: Callable[[Request], Awaitable[Response]]
        ):
            response = await call_next(request)
            response.headers["X-Path"] = request.path
            return response

        app.add_middleware(logging_middleware)

        @app.get("/users/{user_id:int}")
        async def get_user(request: Request, user_id: int):
            return json_response({"user_id": user_id})

        client = TestClient(app)
        response = client.get("/users/123")

        assert response.status_code == 200
        assert response.headers.get("x-path") == "/users/123"
        data = response.json()
        assert data["user_id"] == 123


if __name__ == "__main__":
    pytest.main([__file__])
