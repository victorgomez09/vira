"""
Router class for Vira framework.

Manages collections of routes and handles route matching and dispatch.
"""

from typing import List, Optional, Set, Callable, Awaitable, Dict
from .route import Route
from ..request import Request
from ..response import Response
from ..status import HTTPStatus


class APIRouter:
    """
    Advanced router that manages a collection of routes with support for:
    - Route prefixes
    - Dynamic path segments with type conversion
    - Route priority and matching order
    """

    def __init__(self, prefix: str = ""):
        """
        Initialize an APIRouter.

        Args:
            prefix: URL prefix to apply to all routes in this router
        """
        self.prefix = prefix.rstrip("/")
        self.routes: List[Route] = []
        self._route_definition_order: Dict[Route, int] = (
            {}
        )  # Maps routes to their definition order

    def _calculate_route_specificity(self, route: Route) -> tuple:
        """
        Calculate route specificity for sorting purposes.

        Returns a tuple that can be used for sorting routes from most specific to least specific.
        Higher values in the tuple indicate higher specificity.

        Args:
            route: The route to calculate specificity for

        Returns:
            Tuple of (priority, literal_segments, total_segments, -definition_order)
        """
        # Handle root path specially
        if route.path == "/":
            segments = [""]
        else:
            segments = route.path.strip("/").split("/")

        # Count literal segments (non-parameterized)
        literal_segments = sum(1 for seg in segments if not seg.startswith("{"))
        total_segments = len(segments)

        # Get definition order (default to 0 if not found)
        definition_order = self._route_definition_order.get(route, 0)

        return (
            route.priority,  # User-defined priority (highest precedence)
            literal_segments,  # More literal segments = more specific
            total_segments,  # More total segments = more specific
            -definition_order,  # Earlier definition wins ties
        )

    def add_route(
        self,
        path: str,
        handler: Callable[..., Awaitable[Response]],
        methods: Optional[Set[str]] = None,
        priority: int = 0,
    ) -> Route:
        """
        Add a route to this router.

        Args:
            path: URL path pattern (supports {param}, {param:type}, *, **)
            handler: Async function that handles the request
            methods: Set of HTTP methods this route accepts
            priority: Route priority for matching order (higher = checked first)

        Returns:
            The created Route object
        """
        # Apply router prefix to the path
        full_path = self.prefix + path if path != "/" else (self.prefix or "/")

        route = Route(full_path, handler, methods, priority)

        # Track definition order for consistent sorting
        self._route_definition_order[route] = len(self._route_definition_order)

        self.routes.append(route)

        # Sort routes by specificity (most specific first)
        self.routes.sort(key=self._calculate_route_specificity, reverse=True)

        return route

    def include_router(self, router: "APIRouter", prefix: str = "") -> None:
        """
        Include routes from another router with an optional prefix.

        Args:
            router: Router whose routes to include
            prefix: Additional URL prefix to add to all included routes
        """
        # Clean up prefixes
        prefix = prefix.rstrip("/")

        # Combine our prefix with the additional prefix
        combined_prefix = self.prefix + prefix if prefix else self.prefix

        for route in router.routes:
            # The route already has the source router's prefix applied
            # We need to add our combined prefix to it
            new_path = combined_prefix + route.path if combined_prefix else route.path

            new_route = Route(new_path, route.handler, route.methods, route.priority)

            # Track definition order for included routes
            self._route_definition_order[new_route] = len(self._route_definition_order)

            self.routes.append(new_route)

        # Re-sort routes after inclusion using specificity
        self.routes.sort(key=self._calculate_route_specificity, reverse=True)

    def find_route(self, path: str, method: str) -> Optional[tuple[Route, dict]]:
        """
        Find a route that matches the given path and method.

        Args:
            path: Request path
            method: HTTP method

        Returns:
            Tuple of (matching Route, path_params dict) or None if no match found
        """
        for route in self.routes:
            matches, path_params = route.matches(path, method)
            if matches:
                return route, path_params
        return None

    async def handle_request(self, request: Request) -> Response:
        """
        Handle an HTTP request by finding and executing the appropriate route.

        Args:
            request: The HTTP request

        Returns:
            Response from the matched route handler or 404/405 error
        """
        result = self.find_route(request.path, request.method)

        if result is None:
            # Check if path exists with different method
            path_exists = any(
                route.matches(request.path, "GET")[0]
                or route.matches(request.path, "POST")[0]
                or route.matches(request.path, "PUT")[0]
                or route.matches(request.path, "DELETE")[0]
                or route.matches(request.path, "PATCH")[0]
                or route.matches(request.path, "HEAD")[0]
                or route.matches(request.path, "OPTIONS")[0]
                for route in self.routes
            )

            if path_exists:
                # Path exists but method not allowed
                return Response(
                    "Method Not Allowed",
                    status_code=HTTPStatus.HTTP_405_METHOD_NOT_ALLOWED,
                    headers={"allow": self._get_allowed_methods(request.path)},
                )
            else:
                # Path doesn't exist
                return Response("Not Found", status_code=HTTPStatus.HTTP_404_NOT_FOUND)

        route, path_params = result

        # Set path parameters on the request
        request.path_params = path_params

        return await route.handle(request)

    def _get_allowed_methods(self, path: str) -> str:
        """
        Get allowed methods for a path.

        Args:
            path: Request path

        Returns:
            Comma-separated string of allowed methods
        """
        methods = set()
        for route in self.routes:
            for method in route.methods:
                matches, _ = route.matches(path, method)
                if matches:
                    methods.add(method)

        return ", ".join(sorted(methods))

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

        def decorator(
            handler: Callable[..., Awaitable[Response]],
        ) -> Callable[..., Awaitable[Response]]:
            self.add_route(path, handler, methods, priority)
            return handler

        return decorator

    def get(self, path: str, priority: int = 0):
        """Decorator for GET routes."""
        return self.route(path, {"GET"}, priority)

    def post(self, path: str, priority: int = 0):
        """Decorator for POST routes."""
        return self.route(path, {"POST"}, priority)

    def put(self, path: str, priority: int = 0):
        """Decorator for PUT routes."""
        return self.route(path, {"PUT"}, priority)

    def delete(self, path: str, priority: int = 0):
        """Decorator for DELETE routes."""
        return self.route(path, {"DELETE"}, priority)

    def patch(self, path: str, priority: int = 0):
        """Decorator for PATCH routes."""
        return self.route(path, {"PATCH"}, priority)

    def head(self, path: str, priority: int = 0):
        """Decorator for HEAD routes."""
        return self.route(path, {"HEAD"}, priority)

    def options(self, path: str, priority: int = 0):
        """Decorator for OPTIONS routes."""
        return self.route(path, {"OPTIONS"}, priority)

    def __repr__(self) -> str:
        route_count = len(self.routes)
        return f"<Router routes={route_count}>"
