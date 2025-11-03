# Vira Middleware Architecture Guide

This guide provides an in-depth look at Vira's middleware system, its architecture, implementation decisions, and best practices.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Implementation Details](#implementation-details)
- [Chain Building Strategy](#chain-building-strategy)
- [Execution Order](#execution-order)
- [Performance Considerations](#performance-considerations)
- [Best Practices](#best-practices)
- [Advanced Patterns](#advanced-patterns)
- [Troubleshooting](#troubleshooting)

## Architecture Overview

Vira's middleware system is built around the concept of a middleware chain that creates a processing pipeline for HTTP requests and responses. The system is designed to be:

- **Simple**: Easy to understand and use
- **Flexible**: Supports various middleware patterns
- **Performant**: Optimized for high-throughput applications
- **Debuggable**: Clear execution flow and error handling

### Core Components

```
Vira Application
├── MiddlewareChain (vira/middleware/middlewarechain.py)
│   ├── middleware_list: List[MiddlewareCallable]
│   └── build() -> Callable - Builds the middleware chain
├── Middleware Functions (async callables)
│   ├── request: Request object
│   ├── call_next: Async function to call next middleware
│   └── return: Response object
└── Route Handlers (final destination)
```

## Implementation Details

### MiddlewareChain Class

Located in `vira/middleware/middlewarechain.py`, the `MiddlewareChain` class manages middleware registration and chain building:

```python
class MiddlewareChain:
    def __init__(self):
        self.middleware_list: List[MiddlewareCallable] = []

    def add_middleware(self, middleware: MiddlewareCallable) -> None:
        """Add middleware to the stack."""
        self.middleware_list.append(middleware)

    def build(self, final_handler: Callable) -> Callable:
        """Build the complete middleware chain."""
        # Creates a new chain each time to ensure isolation
```

### MiddlewareCallable Protocol

All middleware must conform to this signature:

```python
from typing import Protocol, Callable, Awaitable

class MiddlewareCallable(Protocol):
    async def __call__(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        ...
```

### Chain Building Process

The middleware chain is built by creating nested function calls:

```python
# Example with 3 middleware: [A, B, C]
# Final chain looks like:
# A(request, lambda: B(request, lambda: C(request, lambda: route_handler(request))))
```

## Chain Building Strategy

### When the Chain is Built

Vira builds the middleware chain **once when middleware is added**, not for every request. The chain is rebuilt only when the middleware configuration changes during application setup.

#### Chain Building Lifecycle

```python
# 1. Application initialization
app = Vira()  # Empty chain created

# 2. Middleware registration (chain rebuilt each time)
app.add_middleware(middleware_a)  # Chain: [A] -> router
app.add_middleware(middleware_b)  # Chain: [A, B] -> router
app.add_middleware(middleware_c)  # Chain: [A, B, C] -> router

# 3. Request handling (uses pre-built chain)
# The same chain instance handles all requests
```

#### Why Rebuild on Middleware Addition

The chain is rebuilt whenever middleware is added to ensure:

1. **Immutable Chain**: Once built, the middleware chain becomes a
   nested set of closures that cannot be modified. Adding new middleware
   requires rebuilding the entire chain.

2. **Correct Order**: Middleware must be applied in the same order as
   registration to achieve the expected "onion" pattern where the
   first registered middleware is the outermost layer.

3. **Performance Trade-off**: While rebuilding seems expensive, it
   only happens at application startup or during middleware registration.
   The resulting chain executes with zero overhead per request.

4. **Simplicity**: This approach keeps the middleware system simple
   and predictable compared to alternatives like dynamic dispatch
   or runtime chain modification.

### Performance Characteristics

This approach provides excellent performance because:

#### **Single Build per Middleware Addition**

```python
# Chain built once during setup
app.add_middleware(logging_middleware)     # Build #1
app.add_middleware(auth_middleware)        # Build #2
app.add_middleware(cors_middleware)        # Build #3

# All requests use the final pre-built chain
# No per-request overhead
```

#### **Optimized Request Handling**

```python
# Each request uses the same pre-built chain
async def handle_request(request):
    # No chain building - direct execution
    return await self._app_with_middleware(request)
```

### Memory and State Management

#### **Shared Chain, Isolated Execution**

```python
# The chain structure is shared (memory efficient)
chain = middleware_a -> middleware_b -> middleware_c -> route_handler

# But each request gets its own execution context
async def middleware_a(request, call_next):
    local_state = {}  # Fresh for each request
    response = await call_next(request)  # Calls middleware_b
    return response
```

#### **No State Pollution**

```python
# Each request execution is independent
async def stateful_middleware(request, call_next):
    # This local state is per-request, not shared
    start_time = time.time()
    response = await call_next(request)
    response.headers['X-Duration'] = str(time.time() - start_time)
    return response
```

### Implementation in Vira.add_middleware()

```python
def add_middleware(self, middleware_func: Callable) -> None:
    """Add middleware and rebuild the chain."""

    # Add to chain and rebuild immediately
    self.middleware_chain.add(middleware_func)
    self._app_with_middleware = self._build_middleware_chain()
```

### Dynamic Middleware (Advanced)

While not commonly used, you can add middleware dynamically:

```python
# During application runtime (not recommended for production)
if debug_mode:
    app.add_middleware(debug_middleware)  # Chain rebuilt once
```

**Note**: Dynamic middleware addition should be done during application setup, not during request handling, as it rebuilds the entire chain.

## Execution Order

### Registration vs. Execution Order

**Key Principle**: Middleware executes in the **same order as registration**.

```python
app.add_middleware(middleware_a)  # Registered 1st
app.add_middleware(middleware_b)  # Registered 2nd
app.add_middleware(middleware_c)  # Registered 3rd

# Request flow: A → B → C → Route Handler
# Response flow: C → B → A → Client
```

## Performance Considerations

### Optimization Strategies

1. **Keep Middleware Lightweight**

```python
# Good: Minimal processing
async def fast_middleware(request, call_next):
    request.state.start_time = time.time()
    return await call_next(request)

# Avoid: Heavy computations
async def slow_middleware(request, call_next):
    complex_computation()  # Bad!
    return await call_next(request)
```

2. **Use Early Returns**

```python
async def auth_middleware(request, call_next):
    # Early return for public endpoints
    if request.path.startswith('/public'):
        return await call_next(request)

    # Auth logic only for protected routes
    if not valid_token(request):
        return unauthorized_response()

    return await call_next(request)
```

3. **Async-Friendly Operations**

```python
async def database_middleware(request, call_next):
    # Use async database operations
    user = await get_user_async(request.headers.get('user-id'))
    request.state.user = user
    return await call_next(request)
```

## Middleware Chain Building and Testing

### Optimized Chain Building

As of the latest version, Vira has been optimized for better performance:

- **Startup Building**: The middleware chain is built once during application startup, not on every request
- **No Runtime Rebuilding**: Middleware cannot be added after the application has started
- **Better Performance**: Zero overhead per request once the chain is built

### Testing Considerations

When writing tests for Vira applications with middleware, you may need to manually build the middleware chain since tests don't go through the normal ASGI startup process:

```python
@pytest.mark.asyncio
async def test_middleware_functionality():
    app = Vira()

    @app.middleware()
    async def test_middleware(request, call_next):
        response = await call_next(request)
        response.headers["X-Test"] = "applied"
        return response

    @app.get("/")
    async def home(request):
        return text_response("Hello")

    # Build middleware chain before testing
    await app._build_middleware_chain()

    # Now test the application...
    scope = {"type": "http", "method": "GET", "path": "/", ...}
    await app(scope, receive, send)
```

**Important**: Always call `await app._build_middleware_chain()` in your tests after adding middleware but before making ASGI calls.

````

## Advanced Patterns

This section covers advanced middleware patterns commonly used in production applications.

**Required imports for examples:**
```python
from vira import Vira, Request
from vira.response import json_response, Response
import time
import uuid
import logging
import traceback
````

### 1. Timing Middleware

Middleware for measuring request processing time:

```python
import time

async def timing_middleware(request: Request, call_next):
    """Middleware that measures request processing time."""
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response

app.add_middleware(timing_middleware)
```

### 2. Request ID Middleware

Adding unique request identifiers for tracing:

```python
import uuid

async def request_id_middleware(request: Request, call_next):
    """Middleware that adds unique request ID to each request."""
    request_id = str(uuid.uuid4())[:8]

    # Store in request for use in handlers (if Request supports state)
    # request.state.request_id = request_id  # Uncomment if available

    response = await call_next(request)

    # Add request ID to response headers
    response.headers["X-Request-ID"] = request_id

    return response

app.add_middleware(request_id_middleware)
```

### 3. Rate Limiting Middleware

Simple rate limiting implementation (production systems should use Redis or similar):

```python
import time

async def rate_limit_middleware(request: Request, call_next):
    """Simple rate limiting middleware (demo purposes only)."""
    # Initialize storage if not exists
    if not hasattr(rate_limit_middleware, 'requests'):
        rate_limit_middleware.requests = {}

    # Get client IP (simplified - use proper IP detection in production)
    client_ip = request.headers.get("x-forwarded-for", "unknown").split(',')[0]
    current_time = time.time()

    # Clean old entries (older than 1 minute)
    rate_limit_middleware.requests = {
        ip: timestamps for ip, timestamps in rate_limit_middleware.requests.items()
        if any(t > current_time - 60 for t in timestamps)
    }

    # Count requests from this IP in the last minute
    if client_ip not in rate_limit_middleware.requests:
        rate_limit_middleware.requests[client_ip] = []

    recent_requests = [
        t for t in rate_limit_middleware.requests[client_ip]
        if t > current_time - 60
    ]

    # Check rate limit (60 requests per minute)
    if len(recent_requests) >= 60:
        return json_response(
            {"error": "Rate limit exceeded. Try again later."},
            status_code=429
        )

    # Record this request
    rate_limit_middleware.requests[client_ip] = recent_requests + [current_time]

    return await call_next(request)

app.add_middleware(rate_limit_middleware)
```

### 4. Authentication Middleware

Authentication middleware with early returns for public endpoints:

```python
async def auth_middleware(request: Request, call_next):
    """Authentication middleware with route-based logic."""
    # Skip auth for public endpoints (early return pattern)
    public_paths = ["/", "/health", "/docs", "/login"]
    if request.path in public_paths or request.path.startswith("/public"):
        return await call_next(request)

    # Check for authentication token
    auth_header = request.headers.get("authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return json_response(
            {"error": "Missing or invalid authorization header"},
            status_code=401
        )

    token = auth_header.split(" ")[1]

    # Validate token (simplified)
    if not validate_token(token):  # Implement your token validation
        return json_response(
            {"error": "Invalid token"},
            status_code=401
        )

    # Add user info to request for downstream handlers
    # request.state.user = get_user_from_token(token)  # If state available

    return await call_next(request)

def validate_token(token: str) -> bool:
    """Implement your token validation logic."""
    return token == "valid-demo-token"  # Simplified for demo

app.add_middleware(auth_middleware)
```

### 5. Class-Based Middleware

Middleware implemented as a class for complex state management:

```python
import time

class ApplicationStateMiddleware:
    """Class-based middleware for managing application state."""

    def __init__(self, app_name: str, version: str):
        self.app_name = app_name
        self.version = version
        self.startup_time = time.time()
        self.request_count = 0

    async def __call__(self, request: Request, call_next):
        # Increment request counter
        self.request_count += 1

        # Add app info to headers (or request state if available)
        response = await call_next(request)

        # Add metadata to response
        response.headers.update({
            "X-App-Name": self.app_name,
            "X-App-Version": self.version,
            "X-App-Uptime": str(time.time() - self.startup_time),
            "X-Request-Count": str(self.request_count)
        })

        return response

app.add_middleware(ApplicationStateMiddleware("MyApp", "1.0.0"))
```

### 6. Error Handling Middleware

Custom error handling and logging:

```python
import logging
import traceback

logger = logging.getLogger(__name__)

async def error_handling_middleware(request: Request, call_next):
    """Middleware for comprehensive error handling."""
    try:
        response = await call_next(request)
        return response

    except ValueError as e:
        # Handle specific exceptions
        logger.warning(f"ValueError in {request.path}: {str(e)}")
        return json_response(
            {"error": "Invalid input", "message": str(e)},
            status_code=400
        )

    except PermissionError as e:
        # Handle permission errors
        logger.warning(f"Permission denied for {request.path}: {str(e)}")
        return json_response(
            {"error": "Access denied"},
            status_code=403
        )

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error in {request.path}: {str(e)}")
        logger.error(traceback.format_exc())

        return json_response(
            {"error": "Internal server error"},
            status_code=500
        )

app.add_middleware(error_handling_middleware)
```

### 7. CORS Middleware (Custom Implementation)

Custom CORS middleware showing advanced patterns:

```python
async def custom_cors_middleware(request: Request, call_next):
    """Custom CORS middleware with dynamic origin checking."""

    # Handle preflight requests
    if request.method == "OPTIONS":
        response = Response("", status_code=200)
    else:
        response = await call_next(request)

    # Get origin from request
    origin = request.headers.get("origin")

    # Dynamic origin validation
    allowed_origins = ["http://localhost:3000", "https://myapp.com"]
    if origin in allowed_origins:
        response.headers["Access-Control-Allow-Origin"] = origin

    # Set other CORS headers
    response.headers.update({
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Credentials": "true",
        "Access-Control-Max-Age": "86400"  # 24 hours
    })

    return response

app.add_middleware(custom_cors_middleware)
```

### 8. Conditional Middleware

Middleware that applies different logic based on conditions:

```python
async def conditional_middleware(request: Request, call_next):
    """Middleware with conditional logic based on request properties."""

    # Different behavior for API vs web routes
    if request.path.startswith("/api/"):
        # API-specific logic
        response = await call_next(request)
        response.headers["X-API-Version"] = "v1"
        return response

    elif request.path.startswith("/admin/"):
        # Admin-specific logic (additional security)
        if not request.headers.get("x-admin-token"):
            return json_response(
                {"error": "Admin access required"},
                status_code=403
            )

        response = await call_next(request)
        response.headers["X-Admin-Access"] = "true"
        return response

    else:
        # Default behavior for web routes
        return await call_next(request)

app.add_middleware(conditional_middleware)
```

### Best Practices for Advanced Middleware

1. **Performance**: Keep middleware lightweight and use early returns
2. **Error Handling**: Always wrap `call_next()` in try-catch for robust error handling
3. **State Management**: Use class-based middleware for complex state requirements
4. **Security**: Validate inputs and sanitize data in security-related middleware
5. **Logging**: Include request context (path, method, headers) in log messages
6. **Testing**: Write comprehensive tests for middleware, especially error conditions

### Troubleshooting

Common middleware issues and solutions:

#### Middleware Not Executing

**Issue**: Middleware doesn't seem to run.

**Solutions**:

- Check middleware registration order
- Ensure `await call_next(request)` is called
- Verify no exceptions are silently caught

#### Performance Issues

**Issue**: Slow request processing.

**Solutions**:

- Profile middleware execution time
- Remove heavy computations from middleware
- Use async operations for I/O

#### State Conflicts

**Issue**: Middleware state interfering with each other.

**Solutions**:

- Use class-based middleware for isolated state
- Avoid global variables in middleware functions
- Use request-scoped storage patterns

### Migration Notes

If you have existing code that relied on the old behavior:

- **Before**: Middleware chain was built on-demand during requests
- **After**: Middleware chain is built once during startup
- **Testing**: Add `await app._build_middleware_chain()` to your test setup

This change improves performance but requires explicit middleware chain building in test scenarios.
