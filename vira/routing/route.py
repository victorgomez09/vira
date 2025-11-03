"""
Route class for Vira framework.

Represents an individual route with path, method, and handler.
"""

import re
import uuid
import inspect
from typing import Callable, Awaitable, Optional, Set, Dict, Any, Union, get_args, get_origin
from ..request import Request
from ..response import Response


class Route:
    """
    Represents a single route with path, HTTP method(s), and handler function.

    Supports dynamic path segments, type conversion, priority-based matching,
    and automatic parameter injection into handler functions.

    Attributes:
        path (str): Normalized URL path pattern. Trailing slashes are removed except
                    for root ("/"). Examples: "/users", "/users/{id:int}", "/files/{filepath:multipath}"

        handler (Callable): Async function that handles requests matching this route.
                            Can accept path parameters and Request-annotated parameters.

        methods (Set[str]): Set of HTTP methods this route accepts (e.g., {"GET", "POST"}).
                            Defaults to {"GET"} if not specified.

        priority (int): Route matching priority. Higher values are checked first.
                        Useful for ensuring specific routes match before generic ones.

        route_regex (re.Pattern): Compiled regex pattern for matching incoming request paths.
                                 Generated from the path pattern during initialization.

        param_types (Dict[str, Any]): Maps path parameter names to their expected types.
                                      Types can be: str, int, float, uuid.UUID, or "multipath".
                                      Maintains insertion order (Python 3.7+).

        segment_count (int): Number of path segments in the route pattern.
                             Used for quick filtering before expensive regex matching.

        has_multipath_parameter (bool): True if route contains a multipath parameter ({name:multipath}).
                                        Multipath parameters can match multiple segments.

        handler_params (list[str]): List of all parameter names in the handler function signature.
                                    Includes both path parameters and any typed parameters.

        request_params (list[str]): List of parameter names that expect Request type injection.
                                    Only includes parameters with explicit Request type annotations.

        handler_path_params (set[str]): Set of path parameter names from handler signature.
                                        Excludes typed injection parameters.

        expected_path_params (list[str]): List of path parameters that exist in both
                                          the route pattern and handler signature.
                                          Used for automatic parameter injection.

    Example:
        >>> async def get_user(user_id: int, request: Request) -> Response:
        ...     return Response(f"User {user_id}")
        >>>
        >>> route = Route("/users/{user_id:int}", get_user, {"GET"}, priority=10)
        >>> matches, params = route.matches("/users/123", "GET")
        >>> # matches=True, params={"user_id": 123}
    """

    def __init__(
        self,
        path: str,
        handler: Callable[..., Awaitable[Response]],
        methods: Optional[Set[str]] = None,
        priority: int = 0,
    ):
        """
        Initialize a Route.

        Args:
            path: URL path pattern (e.g., "/users", "/users/{user_id:int}", "/files/{filepath:multipath}")
            handler: Async function that handles the request
            methods: Set of HTTP methods this route accepts (default: {"GET"})
            priority: Route priority for matching order (higher = checked first, default: 0)
        """
        self.path = path.rstrip("/") or "/"  # Normalize path
        self.handler = handler
        self.methods = methods or {"GET"}
        self.priority = priority

        # Note: route_regex will be set during initialization, so it's never actually None at runtime
        self.route_regex: re.Pattern = None  # type: ignore
        self.param_types: Dict[str, Any] = {}
        self.segment_count: int = 0
        self.has_multipath_parameter: bool = False
        self.handler_params: list[str] = []
        self.request_params: list[str] = []
        self.handler_path_params: set[str] = set()
        self.expected_path_params: list[str] = []

        if invalid_methods := self._invalid_http_methods():
            raise ValueError(f"Invalid HTTP methods: {invalid_methods}")

        # Parse path pattern and compile regex
        self.route_regex, self.param_types = self._compile_route_pattern()

        # Precompute segment count for optimization
        self.segment_count = self._count_path_segments(self.path)
        self.has_multipath_parameter = any(
            param_type == "multipath" for param_type in self.param_types.values()
        )

        # Inspect handler function signature for automatic parameter injection
        self._inspect_handler_signature()

    def _inspect_handler_signature(self) -> None:
        """
        Inspect the handler function signature to determine parameter injection requirements.

        Uses type annotations to determine what should be injected:
        - Parameters annotated with Request type get Request object injection
        - Parameters matching route path parameters get path parameter injection
        """
        sig = inspect.signature(self.handler)
        self.handler_params = list(sig.parameters.keys())
        self.request_params = []
        self.handler_path_params = set()

        # Analyze each parameter based on its type annotation
        for param_name, param in sig.parameters.items():
            if param.annotation == Request:
                self.request_params.append(param_name)
            elif param_name in self.param_types:
                # Parameter matches a route path parameter
                self.handler_path_params.add(param_name)

        # Get expected path parameter names that actually exist in route
        self.expected_path_params = [
            param for param in self.handler_path_params if param in self.param_types
        ]

        # Validate parameter consistency
        self._validate_parameter_consistency(sig)

    def _validate_parameter_consistency(self, sig: inspect.Signature) -> None:
        """
        Validate that path parameters and handler parameters are consistent.

        Args:
            sig: Handler function signature
        """
        # Check that all required parameters exist in both route and handler
        self._validate_parameter_existence()

        # Validate parameter types if annotated
        self._validate_parameter_types(sig)

    def _validate_parameter_existence(self) -> None:
        """
        Validate that path parameters exist in both route pattern and handler signature.

        All route path parameters MUST have corresponding handler parameters.
        Handler path parameters MUST exist in the route pattern.
        """
        path_params = set(self.param_types.keys())

        # All route path parameters MUST have corresponding handler parameters
        missing_in_handler = path_params - self.handler_path_params
        if missing_in_handler:
            raise ValueError(
                f"Route pattern '{self.path}' defines path parameters {missing_in_handler} "
                f"but handler function does not have corresponding parameters. "
                f"Handler path parameters: {self.handler_path_params}"
            )

        # Check that handler path parameters exist in the route
        missing_in_route = self.handler_path_params - path_params
        if missing_in_route:
            raise ValueError(
                f"Handler function expects path parameters {missing_in_route} "
                f"but route pattern '{self.path}' only defines {path_params}"
            )

    def _validate_parameter_types(self, sig: inspect.Signature) -> None:
        """
        Validate that handler parameter type annotations match route parameter types.

        Args:
            sig: Handler function signature
        """
        for param_name in self.expected_path_params:
            handler_param = sig.parameters[param_name]
            path_param_type = self.param_types[param_name]

            # If handler parameter has type annotation, validate it matches
            if handler_param.annotation != inspect.Parameter.empty:
                annotation = handler_param.annotation

                # Define expected types for each path parameter type
                expected_types = {
                    int: {int},
                    float: {float},
                    uuid.UUID: {uuid.UUID},
                    str: {str},
                    "multipath": {str},
                }

                # Check if annotation matches expected type
                if annotation not in expected_types.get(path_param_type, set()):
                    raise ValueError(
                        f"Parameter '{param_name}' type mismatch: "
                        f"route expects {path_param_type} but handler annotated as {annotation}"
                    )

    def _compile_route_pattern(self) -> tuple[re.Pattern, dict[str, Any]]:
        """
        Compile route pattern into regex and extract parameter information.

        Supports:
        - Static paths: /users
        - Dynamic segments: /users/{user_id}, /users/{user_id:int}
        - Multipath parameters: /files/{filepath:multipath} (captures remaining path)

        Returns:
            Tuple of (compiled regex, parameter types with preserved order)
        """
        # Validate that wildcard characters are not used
        if "*" in self.path:
            raise ValueError(
                "Wildcard patterns (*/**) are no longer supported. Use multipath parameters instead: {name:multipath}"
            )

        param_types = {}  # Using dict to maintain insertion order (Python 3.7+)
        regex_parts = []

        i = 0
        while i < len(self.path):
            i = self._process_path_segment(self.path, i, regex_parts, param_types)

        regex_pattern = "^" + "".join(regex_parts) + "$"
        return re.compile(regex_pattern), param_types

    def _count_path_segments(self, path: str) -> int:
        """Count the number of path segments by counting '/' characters."""
        # Remove leading slash and split by '/'
        clean_path = path.lstrip("/")
        if not clean_path:
            return 1

        return clean_path.count("/") + 1

    def _process_path_segment(
        self,
        path_segment: str,
        index: int,
        regex_parts: list[str],
        param_types: dict[str, Any],
    ) -> int:
        """
        Process a single segment of the path pattern and update regex.

        Args:
            path_segment: The full path pattern string
            index: Current index in the path pattern
            regex_parts: List to collect regex parts
            param_types: Dictionary to collect parameter types

        Returns:
            The new index position after processing this segment
        """
        if path_segment[index] == "{":
            return self._process_path_parameter(
                path_segment, index, regex_parts, param_types
            )
        else:
            return self._process_literal_segment(path_segment, index, regex_parts)

    def _process_path_parameter(
        self,
        pattern: str,
        index: int,
        regex_parts: list[str],
        param_types: dict[str, Any],
    ) -> int:
        """
        Parses parameter specifications like {user_id} or {user_id:int} from
        the path pattern and builds corresponding regex patterns.

        Args:
            pattern: The full path pattern string being processed
            index: Current index position in the pattern
            regex_parts: List to collect regex parts (modified in-place).
                         The appropriate regex pattern for this parameter
                         will be appended to this list.
            param_types: Dictionary to collect parameter type information
                         (modified in-place). Maps parameter names to their
                         expected types (int, str, uuid.UUID, or "path").

        Returns:
            The new index position after processing this parameter (after '}')

        Raises:
            ValueError: If parameter specification is malformed (unclosed braces,
                        invalid type specifications, etc.)

        Example:
            For pattern "/users/{user_id:int}/posts", when index points to '{':
            - Extracts "user_id:int"
            - Adds r"(\d+)" to regex_parts
            - Adds {"user_id": int} to param_types
            - Returns index pointing after '}'
        """
        end = pattern.find("}", index)
        if end == -1:
            raise ValueError(f"Unclosed parameter at position {index}")

        param_spec = pattern[index + 1 : end]
        param_name, param_type = self._parse_parameter_specification(param_spec)

        param_types[param_name] = param_type

        regex_pattern = self._get_regex_for_parameter_type(param_type)
        regex_parts.append(regex_pattern)

        return end + 1

    def _process_literal_segment(
        self, pattern: str, index: int, regex_parts: list[str]
    ) -> int:
        """
        Process a complete literal segment until next '{' or end of pattern.

        Args:
            pattern: The full path pattern string
            index: Current index position in the pattern
            regex_parts: List to collect regex parts (modified in-place).
                         The escaped literal segment will be appended.

        Returns:
            The new index position after processing this literal segment

        Example:
            For pattern "/users/profile/{id}", starting at index 1:
            - Processes "users/profile/" as one unit
            - Escapes special regex characters as needed
            - Returns index pointing to '{'
        """
        start = index

        # Find the next '{' or end of string
        next_param_index = pattern.find("{", index)
        if next_param_index == -1:
            end_index = len(pattern)
        else:
            end_index = next_param_index

        # Extract the literal segment
        literal_segment = pattern[start:end_index]

        # Escape special regex characters in the entire segment and append
        escaped_segment = re.escape(literal_segment)
        regex_parts.append(escaped_segment)

        return end_index

    def _parse_parameter_specification(self, param_spec: str) -> tuple[str, Any]:
        """
        Parse parameter specification like 'user_id' or 'user_id:int'.

        Args:
            param_spec: Parameter specification string (e.g., 'user_id', 'user_id:int', 'filepath:multipath')

        Returns:
            Tuple of (parameter_name, parameter_type)
            If no type specified, defaults to str
        """
        if ":" in param_spec:
            param_name, type_name = param_spec.split(":", 1)
            param_type = self._get_param_type(type_name)
        else:
            param_name = param_spec
            param_type = str

        return param_name, param_type

    def _get_regex_for_parameter_type(self, param_type) -> str:
        """Get the appropriate regex pattern for a parameter type."""
        if param_type == int:
            return r"(\d+)"
        elif param_type == float:
            return r"(\d+(?:\.\d+)?)"
        elif param_type == uuid.UUID:
            return r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"
        elif param_type == "multipath":
            # Special case for 'multipath' type - matches any remaining path (like catch-all but captured)
            return r"(.*)"
        else:  # str or any other type
            return r"([^/]+)"

    def _get_param_type(self, type_name: str) -> type:
        """Get Python type from string type name."""
        type_map = {
            "str": str,
            "int": int,
            "float": float,
            "uuid": uuid.UUID,
            "multipath": "multipath",  # Special marker for multipath type
        }

        if type_name not in type_map:
            raise ValueError(f"Unsupported parameter type: {type_name}")

        return type_map[type_name]

    def _invalid_http_methods(self) -> Set[str]:
        """
        Returns a set of invalid HTTP methods for this route.
        """
        valid_methods = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        invalid_methods = self.methods - valid_methods

        return invalid_methods

    def matches(self, path: str, method: str) -> tuple[bool, dict[str, Any]]:
        """
        Check if this route matches the given path and method.

        Args:
            path: Request path
            method: HTTP method

        Returns:
            Tuple of (matches: bool, path_params: dict)
        """
        # Check method first (quick fail)
        if method.upper() not in self.methods:
            return False, {}

        # Quick segment count check before expensive regex matching
        request_segment_count = self._count_path_segments(path)
        normalized_request_segments = self._count_path_segments(path.rstrip("/") or "/")

        # Route can match if:
        # 1. Original segment counts are equal (handles exact matches)
        # 2. Normalized segment counts are equal (handles trailing slash normalization)
        # 3. Request has more segments AND route has a multipath parameter (handles multipath params)
        segment_match = (
            request_segment_count == self.segment_count
            or normalized_request_segments == self.segment_count
            or (
                request_segment_count > self.segment_count
                and self.has_multipath_parameter
            )
        )

        if not segment_match:
            return False, {}

        # For routes with multipath parameters, try matching original path first
        # This handles cases like /files/ matching /files/{path:multipath} with empty path
        if self.has_multipath_parameter:
            match = self.route_regex.match(path)
            if match:
                # Extract and convert path parameters
                return self._extract_path_parameters(match)

        # Normalize the request path and try matching
        normalized_path = path.rstrip("/") or "/"
        match = self.route_regex.match(normalized_path)
        if not match:
            return False, {}

        # Extract and convert path parameters
        return self._extract_path_parameters(match)

    def _extract_path_parameters(self, match) -> tuple[bool, dict[str, Any]]:
        """Extract and convert path parameters from a regex match."""
        path_params = {}
        for i, param_name in enumerate(self.param_types.keys()):
            raw_value = match.group(i + 1)
            param_type = self.param_types[param_name]

            try:
                if param_type == int:
                    path_params[param_name] = int(raw_value)
                elif param_type == float:
                    path_params[param_name] = float(raw_value)
                elif param_type == uuid.UUID:
                    path_params[param_name] = uuid.UUID(raw_value)
                elif param_type == "multipath":
                    # Multipath type stores the raw string value (like str but matches any path)
                    path_params[param_name] = raw_value
                else:  # str or other
                    path_params[param_name] = raw_value
            except (ValueError, TypeError) as e:
                # Type conversion failed
                return False, {}

        return True, path_params

    # --- Methods for Parameter Binding (Query Params) ---
    def _is_optional_type(self, annotation: Any) -> bool:
        """
        Check if a type annotation is Optional[T] or Union[T, None].
        """
        return get_origin(annotation) is Union and type(None) in get_args(annotation)

    def _unwrap_type(self, annotation: Any) -> type:
        """
        Get the non-Union type from an annotation.

        If it's Optional[T] or Union[T, None], it returns T.
        If it's a simple type (str, int), it returns the type itself.
        """
        if get_origin(annotation) is Union:
            # Union types: remove NoneType and return the remaining type.
            non_none_args = [arg for arg in get_args(annotation) if arg is not type(None)]
            if len(non_none_args) == 1:
                return non_none_args[0]
            # If multiple types remain, or none (shouldn't happen with Optional),
            # default to str to avoid complexity, or handle error.
            return str # Fallback for complex unions not designed for query params

        return annotation

    def _convert_value(self, value: str, target_type: type) -> Any:
        """
        Convert a string value from query params to the target type.
        """
        if target_type is str:
            return value
        if target_type is int:
            return int(value)
        if target_type is float:
            return float(value)
        if target_type is uuid.UUID:
            return uuid.UUID(value)
        
        # Handle Boolean type (case-insensitive conversion)
        if target_type is bool:
            if value.lower() in ('true', '1', 't'):
                return True
            if value.lower() in ('false', '0', 'f'):
                return False
            raise ValueError(f"Cannot convert '{value}' to boolean.")
            
        raise TypeError(f"Unsupported target type for conversion: {target_type}")

    # --- Handle method with Query Parameter Binding ---
    async def handle(self, request: Request) -> Response:
        """
        Handle the request using this route's handler with automatic parameter injection.

        Injects:
        1. Request object (if annotated)
        2. Path parameters (from route match)
        3. Query parameters (from request.query_params)

        Args:
            request: The HTTP request (with path_params populated)

        Returns:
            Response from the handler
        
        Raises:
            ValueError: If a required query parameter is missing and has no default value.
            TypeError: If query parameter conversion fails.
        """
        sig = inspect.signature(self.handler)
        kwargs = {}

        # 1. Inject Request objects and Path parameters (existing logic)
        path_param_names = set(request.path_params.keys())
        
        for param_name, param in sig.parameters.items():
            if param.annotation == Request:
                # Inject the Request object
                kwargs[param_name] = request
            elif param_name in path_param_names:
                # Inject the Path parameter (already type-converted by _extract_path_parameters)
                kwargs[param_name] = request.path_params[param_name]
            # Parameters not handled here are assumed to be Query or Body parameters
        
        # 2. Inject Query Parameters (New Logic)
        for param_name, param in sig.parameters.items():
            
            # Skip parameters already injected (Request object, Path parameters)
            if param_name in kwargs:
                continue

            # Determine if the parameter has an explicit type annotation
            if param.annotation == inspect.Parameter.empty:
                # If no annotation, skip (cannot bind without type info, 
                # or rely on default value which will be used by Python later)
                continue

            # Check if parameter is present in Query Params
            raw_value = request.query_params.get(param_name)
            
            is_optional = self._is_optional_type(param.annotation)
            
            if raw_value is not None:
                # Value found in query params, attempt conversion
                try:
                    target_type = self._unwrap_type(param.annotation)
                    kwargs[param_name] = self._convert_value(raw_value, target_type)
                except (ValueError, TypeError) as e:
                    # Conversion failed (e.g., 'abc' for int) -> Bad Request error (would be caught higher up)
                    print(f"ERROR: Query param '{param_name}' conversion failed: {e}")
                    raise TypeError(f"Invalid type for query parameter '{param_name}'.") from e
            else:
                # Value NOT found in query params
                
                # If optional (Union[T, None]) or has a default value (e.g., q=None, q='default')
                if is_optional or param.default is not inspect.Parameter.empty:
                    # Rely on Python to use the default value (which might be None)
                    pass # Do not add to kwargs, let Python fill it
                else:
                    # Parameter is required, but missing
                    raise ValueError(f"Required query parameter '{param_name}' is missing.")

        return await self.handler(**kwargs)

    def __repr__(self) -> str:
        methods_str = ",".join(sorted(self.methods))
        priority_str = f" priority={self.priority}" if self.priority != 0 else ""
        return f"<Route {methods_str} {self.path}{priority_str}>"
