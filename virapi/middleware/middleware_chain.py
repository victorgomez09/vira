"""
Middleware chain implementation for virapi.

The MiddlewareChain class manages the middleware chain and builds the execution pipeline.
"""

from typing import Callable, Awaitable, List, Protocol
from ..request import Request
from ..response import Response


class MiddlewareCallable(Protocol):
    """Protocol for middleware callables in virapi."""

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process a request through the middleware.

        Args:
            request: The incoming HTTP request
            call_next: Function to call the next middleware in the chain

        Returns:
            The HTTP response
        """
        ...


class MiddlewareChain:
    """
    Manages a chain of middleware for virapi applications.

    The middleware chain follows the "onion" pattern where middleware are executed
    in the same order as registration, with each middleware wrapping the next one.
    """

    def __init__(self):
        """Initialize an empty middleware chain."""
        self._middlewares: List[MiddlewareCallable] = []

    def add(self, middleware: MiddlewareCallable):
        """
        Add middleware to the chain.

        Args:
            middleware: A callable with signature (request, call_next) -> response
        """
        self._middlewares.append(middleware)

    def build(self, endpoint: Callable[[Request], Awaitable[Response]]):
        """
        Build the middleware chain around the given endpoint.

        The middleware are applied in the same order as registration so that the first registered
        middleware becomes the outermost layer in the execution chain.

        Args:
            endpoint: The final handler (usually router.handle_request)

        Returns:
            A callable that represents the complete middleware chain

        Example:
            If middleware are registered as [A, B, C], the execution flow will be:
            Request -> A -> B -> C -> endpoint -> C -> B -> A -> Response
        """
        # Return original endpoint if no middleware
        if not self._middlewares:
            return endpoint

        # Build the chain from endpoint outward by wrapping each middleware
        current_handler = endpoint

        # Process middleware in reverse order (last registered = closest to endpoint)
        for middleware in reversed(self._middlewares):
            # Capture the current handler in a closure
            next_handler = current_handler

            async def middleware_handler(
                request: Request, mw=middleware, next_app=next_handler
            ):
                # Create the call_next function for this middleware
                async def call_next(req: Request):
                    return await next_app(req)

                # Execute the middleware
                return await mw(request, call_next)

            current_handler = middleware_handler

        return current_handler

    def count(self) -> int:
        """Return the number of middleware in the chain."""
        return len(self._middlewares)

    def clear(self):
        """Remove all middleware from the chain."""
        self._middlewares.clear()
