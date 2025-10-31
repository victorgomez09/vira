"""
Vira - A simple ASGI framework for educational purposes.
"""

from typing import Callable, Dict, Any, Awaitable, Union, Optional, Set, List

from .request import Request
from .response import Response, text_response
from .status import HTTPStatus
from .routing import APIRouter
from .middleware import MiddlewareChain, MiddlewareCallable


class Vira:
    """Main Vira application class. To create an application, instantiate this class."""

    def __init__(
        self,
        api_router: Optional[APIRouter] = None,
        max_in_memory_file_size: int = 1024 * 1024,  # 1 MB default
        temp_dir: Optional[str] = None,
    ):
        """Initialize the Vira application.

        Args:
            api_router: Optional router instance. If not provided, a new APIRouter is created.
            max_in_memory_file_size: Maximum size in bytes to keep files in memory before using disk
            temp_dir: Directory for temporary files (None for system default)
        """
        self.api_router = api_router or APIRouter()
        self.middleware_chain = MiddlewareChain()
        self._app_with_middleware: Callable[[Request], Awaitable[Response]] | None = (
            None
        )
        self._middleware_built = False

        # Configure Request class with application-level settings
        Request.max_in_memory_file_size = max_in_memory_file_size
        Request.temp_dir = temp_dir

        # Lifespan event handlers
        self._startup_handlers: List[Callable[[], Awaitable[None]]] = []
        self._shutdown_handlers: List[Callable[[], Awaitable[None]]] = []

        # First startup handler builds middleware chain
        self._startup_handlers.append(self._build_middleware_chain)

        # Add cleanup handler for shutdown
        self._shutdown_handlers.append(self._cleanup_all_requests)

    async def _build_middleware_chain(self):
        """Build the middleware chain during application startup."""
        if not self._middleware_built:
            self._app_with_middleware = self.middleware_chain.build(
                self.api_router.handle_request
            )
            self._middleware_built = True

    async def _cleanup_all_requests(self):
        """Clean up all active requests during application shutdown."""
        Request.cleanup_all_active_requests()

    def include_router(
        self,
        router: APIRouter,
        prefix: str = "",
    ) -> None:
        """
        Include another router in this application.

        Args:
            router: APIRouter to include
            prefix: URL prefix for the included router
        """
        self.api_router.include_router(router, prefix)

    def add_middleware(self, middleware: MiddlewareCallable):
        """
        Add middleware to the application.

        Args:
            middleware: Middleware callable with signature (request, call_next)
        Raises:
            RuntimeError: If middleware is added after application startup
        """

        self.middleware_chain.add(middleware)
        # Middleware chain will be built during startup
        if self._middleware_built:
            raise RuntimeError(
                "Cannot add middleware after application startup. Add all middleware before starting the server."
            )

    def middleware(self):
        """
        Decorator for registering middleware.

        Usage:
            @app.middleware()
            async def my_middleware(request, call_next):
                # pre-processing
                response = await call_next(request)
                # post-processing
                return response
        """

        def decorator(func: MiddlewareCallable) -> MiddlewareCallable:
            self.add_middleware(func)
            return func

        return decorator

    # Lifespan event handlers
    def _register_event_handler(
        self, event_type: str, func: Callable[[], Awaitable[None]]
    ) -> None:
        """
        Internal method to register an event handler.

        Args:
            event_type: Either "startup" or "shutdown"
            func: Async function to call during the event

        Raises:
            ValueError: If event_type is not "startup" or "shutdown"
        """
        if event_type == "startup":
            self._startup_handlers.append(func)
        elif event_type == "shutdown":
            self._shutdown_handlers.append(func)
        else:
            raise ValueError(
                f"Invalid event type: {event_type}. Must be 'startup' or 'shutdown'"
            )

    def on_event(self, event_type: str):
        """
        Register a function to run on application startup or shutdown.

        Args:
            event_type: Either "startup" or "shutdown"

        Returns:
            Decorator function

        Example:
            @app.on_event("startup")
            async def startup_event():
                print("Application starting up!")

            @app.on_event("shutdown")
            async def shutdown_event():
                print("Application shutting down!")
        """

        def decorator(
            func: Callable[[], Awaitable[None]],
        ) -> Callable[[], Awaitable[None]]:
            self._register_event_handler(event_type, func)
            return func

        return decorator

    def add_event_handler(
        self, event_type: str, func: Callable[[], Awaitable[None]]
    ) -> None:
        """
        Add an event handler for startup or shutdown.

        Args:
            event_type: Either "startup" or "shutdown"
            func: Async function to call during the event

        Example:
            async def init_database():
                print("Initializing database...")

            app.add_event_handler("startup", init_database)
        """
        self._register_event_handler(event_type, func)

    async def _run_startup_handlers(self) -> None:
        """Run all registered startup handlers."""
        for handler in self._startup_handlers:
            await handler()

    async def _run_shutdown_handlers(self) -> None:
        """Run all registered shutdown handlers."""
        for handler in self._shutdown_handlers:
            await handler()

    # Route decorator methods
    def route(
        self,
        path: str,
        methods: Optional[Set[str]] = None,
        priority: int = 0,
    ):
        """
        Decorator for registering routes.

        Args:
            path: URL path pattern (supports {param}, {param:type}, *, **)
            methods: Set of HTTP methods this route accepts
            priority: Route priority for matching order (higher = checked first)

        Returns:
            Decorator function
        """
        return self.api_router.route(path, methods, priority)

    def get(self, path: str, priority: int = 0):
        """Decorator for GET routes."""
        return self.api_router.get(path, priority)

    def post(self, path: str, priority: int = 0):
        """Decorator for POST routes."""
        return self.api_router.post(path, priority)

    def put(self, path: str, priority: int = 0):
        """Decorator for PUT routes."""
        return self.api_router.put(path, priority)

    def delete(self, path: str, priority: int = 0):
        """Decorator for DELETE routes."""
        return self.api_router.delete(path, priority)

    def patch(self, path: str, priority: int = 0):
        """Decorator for PATCH routes."""
        return self.api_router.patch(path, priority)

    def head(self, path: str, priority: int = 0):
        """Decorator for HEAD routes."""
        return self.api_router.head(path, priority)

    def options(self, path: str, priority: int = 0):
        """Decorator for OPTIONS routes."""
        return self.api_router.options(path, priority)

    async def __call__(self, scope: Dict[str, Any], receive: Callable, send: Callable):
        """
        ASGI application entrypoint.
        This method is called by the ASGI server (uvicorn for example) for each incoming connection.

        Args:
            scope: Connection scope information
            receive: Callable to receive messages from the client
            send: Callable to send messages to the client
        """

        if scope["type"] == "http":
            await self._handle_http(scope, receive, send)
        elif scope["type"] == "lifespan":
            await self._handle_lifespan(scope, receive, send)
        else:
            await self._handle_unsupported_protocol(send)

    async def _handle_lifespan(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ):
        """
        Handle ASGI lifespan protocol for startup and shutdown events.

        This implements the ASGI lifespan protocol which allows the server
        to notify the application about startup and shutdown events.
        """
        message = await receive()

        if message["type"] == "lifespan.startup":
            try:
                # Run all startup handlers
                await self._run_startup_handlers()
                await send({"type": "lifespan.startup.complete"})
            except Exception as e:
                await send({"type": "lifespan.startup.failed", "message": str(e)})
        elif message["type"] == "lifespan.shutdown":
            try:
                # Run all shutdown handlers
                await self._run_shutdown_handlers()
                await send({"type": "lifespan.shutdown.complete"})
            except Exception as e:
                await send({"type": "lifespan.shutdown.failed", "message": str(e)})

    async def _handle_unsupported_protocol(self, send: Callable):
        """
        Handle unsupported protocol types.
        """
        # For non-HTTP protocols, just close the connection
        await send({"type": "websocket.close", "code": 1000})

    async def _handle_http(
        self, scope: Dict[str, Any], receive: Callable, send: Callable
    ):
        """
        Handle HTTP requests using the middleware stack and routing system.
        """
        request = None
        try:
            # Build Request object and load body from the ASGI receive channel
            request = await Request.from_asgi(scope, receive)

            # Process request through pre-built middleware stack
            if self._app_with_middleware is None:
                raise RuntimeError("Middleware chain not built")
            response = await self._app_with_middleware(request)  # type: ignore[misc]
            # Convert response to ASGI format and send
            asgi_response = response.to_asgi_response()
            await self._send_response(send, asgi_response)

        except Exception as e:
            # Handle errors with 500 response
            error_response = text_response(
                f"Internal Server Error: {str(e)}",
                status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            asgi_response = error_response.to_asgi_response()
            await self._send_response(send, asgi_response)
        finally:
            # Clean up request resources after response is sent
            if request is not None:
                request.cleanup_files()

    async def _send_response(self, send: Callable, asgi_response: Dict[str, Any]):
        """
        Send an ASGI HTTP response.
        """
        # Send response start
        await send(
            {
                "type": "http.response.start",
                "status": asgi_response["status"],
                "headers": asgi_response["headers"],
            }
        )

        # Send response body
        await send(
            {
                "type": "http.response.body",
                "body": asgi_response["body"],
                "more_body": False,
            }
        )
