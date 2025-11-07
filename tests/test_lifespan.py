"""
Tests for virapi lifespan event handling.

Tests the lifespan event registration and execution system,
including ASGI protocol compliance and error handling.
"""

import pytest
from unittest.mock import AsyncMock
from virapi import virapi


class TestLifespanEvents:
    """Test lifespan event handling functionality."""

    def test_event_handler_registration(self):
        """Test both decorator and direct registration methods."""
        app = virapi()

        # Test startup registration
        @app.on_event("startup")
        async def startup_decorator():
            pass

        async def startup_direct():
            pass

        app.add_event_handler("startup", startup_direct)

        # Test shutdown registration
        @app.on_event("shutdown")
        async def shutdown_decorator():
            pass

        async def shutdown_direct():
            pass

        app.add_event_handler("shutdown", shutdown_direct)

        # Verify registration (including built-in handlers)
        assert len(app._startup_handlers) == 3  # 2 user + 1 built-in
        assert len(app._shutdown_handlers) == 3  # 2 user + 1 built-in
        assert startup_decorator in app._startup_handlers
        assert startup_direct in app._startup_handlers
        assert shutdown_decorator in app._shutdown_handlers
        assert shutdown_direct in app._shutdown_handlers

    def test_invalid_event_type_handling(self):
        """Test error handling for invalid event types."""
        app = virapi()

        # Test decorator
        with pytest.raises(ValueError, match="Invalid event type: invalid"):

            @app.on_event("invalid")
            async def invalid_handler():
                pass

        # Test direct registration
        async def handler():
            pass

        with pytest.raises(ValueError, match="Invalid event type: invalid"):
            app.add_event_handler("invalid", handler)

    @pytest.mark.asyncio
    async def test_lifespan_protocol_startup(self):
        """Test ASGI lifespan protocol startup handling."""
        app = virapi()
        startup_called = False

        @app.on_event("startup")
        async def startup_handler():
            nonlocal startup_called
            startup_called = True

        receive = AsyncMock(return_value={"type": "lifespan.startup"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        assert startup_called
        send.assert_called_once_with({"type": "lifespan.startup.complete"})

    @pytest.mark.asyncio
    async def test_lifespan_protocol_shutdown(self):
        """Test ASGI lifespan protocol shutdown handling."""
        app = virapi()
        shutdown_called = False

        @app.on_event("shutdown")
        async def shutdown_handler():
            nonlocal shutdown_called
            shutdown_called = True

        receive = AsyncMock(return_value={"type": "lifespan.shutdown"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        assert shutdown_called
        send.assert_called_once_with({"type": "lifespan.shutdown.complete"})

    @pytest.mark.asyncio
    async def test_lifespan_startup_error_handling(self):
        """Test error handling in lifespan startup."""
        app = virapi()

        @app.on_event("startup")
        async def failing_handler():
            raise RuntimeError("Startup failed")

        receive = AsyncMock(return_value={"type": "lifespan.startup"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        send.assert_called_once_with(
            {"type": "lifespan.startup.failed", "message": "Startup failed"}
        )

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_error_handling(self):
        """Test error handling in lifespan shutdown."""
        app = virapi()

        @app.on_event("shutdown")
        async def failing_handler():
            raise RuntimeError("Shutdown failed")

        receive = AsyncMock(return_value={"type": "lifespan.shutdown"})
        send = AsyncMock()
        scope = {"type": "lifespan"}

        await app._handle_lifespan(scope, receive, send)

        send.assert_called_once_with(
            {"type": "lifespan.shutdown.failed", "message": "Shutdown failed"}
        )

    @pytest.mark.asyncio
    async def test_multiple_lifespan_handlers(self):
        """Test multiple handlers for the same lifespan event."""
        startup_order = []
        shutdown_order = []

        app = virapi()

        @app.on_event("startup")
        async def startup_1():
            startup_order.append("first")

        @app.on_event("startup")
        async def startup_2():
            startup_order.append("second")

        @app.on_event("shutdown")
        async def shutdown_1():
            shutdown_order.append("first")

        @app.on_event("shutdown")
        async def shutdown_2():
            shutdown_order.append("second")

        scope = {"type": "lifespan"}
        sent_messages = []

        async def send(message):
            sent_messages.append(message)

        # Test startup
        async def receive_startup():
            return {"type": "lifespan.startup"}

        await app._handle_lifespan(scope, receive_startup, send)

        assert startup_order == ["first", "second"]
        assert {"type": "lifespan.startup.complete"} in sent_messages

        # Test shutdown
        sent_messages.clear()

        async def receive_shutdown():
            return {"type": "lifespan.shutdown"}

        await app._handle_lifespan(scope, receive_shutdown, send)

        assert shutdown_order == ["first", "second"]
        assert {"type": "lifespan.shutdown.complete"} in sent_messages
