"""
Tests for Vira core application class and ASGI protocol compliance.

This module tests the fundamental ASGI interface implementation and core
application functionality of the Vira framework, including:

- ASGI 3.0 protocol compliance (HTTP protocol)
- Unsupported protocol handling (WebSocket rejection)

This test suite uses direct ASGI interface calls to validate low-level
protocol compliance without depending on the TestClient framework.
"""

import pytest
from vira import Vira, Response, Request


class TestFastASGICore:
    """Test core Vira application functionality."""

    @pytest.mark.asyncio
    async def test_asgi_interface_compliance(self):
        """Test that Vira implements ASGI interface correctly."""
        app = Vira()

        @app.get("/test")
        async def test_route(request: Request):
            return Response("OK")

        # Vira builds middleware chain lazily on first HTTP request,
        # but these tests bypass normal request flow, so we build it explicitly
        await app._build_middleware_chain()

        # Test HTTP scope
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "path_info": "/test",
            "scheme": "http",
            "server": ("127.0.0.1", 8000),
        }

        received_messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            received_messages.append(message)

        await app(scope, receive, send)

        # Verify ASGI response messages
        assert len(received_messages) == 2
        assert received_messages[0]["type"] == "http.response.start"
        assert received_messages[0]["status"] == 200
        assert received_messages[1]["type"] == "http.response.body"
        assert received_messages[1]["body"] == b"OK"
        assert received_messages[1]["more_body"] is False

    @pytest.mark.asyncio
    async def test_unsupported_protocol(self):
        """Test handling of unsupported ASGI protocol types."""
        app = Vira()

        scope = {"type": "websocket"}  # Unsupported protocol

        received_messages = []

        async def receive():
            return {"type": "websocket.connect"}

        async def send(message):
            received_messages.append(message)

        await app(scope, receive, send)

        # Should close websocket connection
        assert len(received_messages) == 1
        assert received_messages[0]["type"] == "websocket.close"
        assert received_messages[0]["code"] == 1000


if __name__ == "__main__":
    print("Running Vira core tests...")
    pytest.main([__file__])
