# Vira v0.3.0 - Complete ASGI Framework with Advanced Routing

A lightweight, educational ASGI framework built from scratch with FastAPI-style routing. Vira provides a clean, modern API for building web applications with decorators, request/response objects, and a powerful modular routing system.

## Features

- � **FastAPI-Style Decorators**: `@app.get("/")`, `@app.post("/")` route registration
- 🔗 **Advanced Routing System**: Path parameters, type conversion, priority routing, and modular organization
- 🎯 **Path Parameters**: Dynamic routes with automatic type conversion (int, str, float, uuid, path)
- � **Modular Routers**: Organize routes with `APIRouter` and prefix-based inclusion
- 🔧 **Middleware System**: Request/response pipeline with authentication, logging, CORS, and custom middleware
- ⚡ **High Performance**: Optimized route matching with segment-count pre-filtering
- 🍪 **Full Cookie Support**: Set, read, delete cookies with all standard attributes
- 📡 **ASGI 3.0 Compatible**: Works with uvicorn, hypercorn, and other ASGI servers
- 🔄 **Request/Response Objects**: High-level abstractions similar to FastAPI
- 📋 **Content Type Detection**: Automatic JSON, HTML, and text content type handling
- 🔍 **Multi-Value Query Params**: Handle parameters with multiple values (tags, filters, etc.)
- 📊 **HTTPStatus Enum**: Complete HTTP status code definitions (100-511)
- 🛡️ **Error Handling**: Automatic 404/405 responses with proper headers
- ⛓️ **Method Chaining**: Fluent API for response building
- 🎯 **All HTTP Methods**: Support for GET, POST, PUT, DELETE, PATCH, HEAD, OPTIONS

## Quick Start

### Basic Application

```python
from vira import Vira, text_response, json_response

# Create the application
app = Vira()

# Define routes using decorators
@app.get("/")
async def home(request):
    return text_response("Welcome to Vira!")

@app.get("/health")
async def health_check(request):
    return json_response({"status": "healthy", "version": "0.3.0"})

@app.post("/echo")
async def echo(request):
    # Access request body as method
    body = request.body()
    data = json.loads(body.decode()) if body else {}
    return json_response({"echo": data})

# Run with: uvicorn your_app:app --reload
```

### Modular API with Routers

```python
from vira import Vira, APIRouter, json_response

# Create main application
app = Vira()

# Create API router for user management
users_router = APIRouter()

@users_router.get("/")
async def list_users(request):
    return json_response({
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"}
        ]
    })

@users_router.post("/")
async def create_user(request):
    body = request.body()
    data = json.loads(body.decode()) if body else {}
    return json_response({
        "created_user": {"id": 999, "name": data.get("name", "Unknown")}
    }, status_code=201)

@users_router.get("/{user_id:int}")
async def get_user(user_id: int):
    # Path parameters are automatically converted and injected
    return json_response({"user_id": user_id, "type": type(user_id).__name__})

# Include router with prefix
app.include_router(users_router, prefix="/api/users")

# Available routes:
# GET  /api/users/         - List users
# POST /api/users/         - Create user
# GET  /api/users/{id}     - Get specific user
```

## Advanced Routing System

Vira provides a powerful routing system with path parameters, type conversion, priority routing, and modular organization.

### Path Parameters with Type Conversion

Define dynamic routes with automatic parameter extraction and type conversion:

```python
from vira import Vira
import uuid

app = Vira()

# String parameters (default type)
@app.get("/users/{username}")
async def get_user_by_name(username: str):
    return json_response({"user": username})

# Integer parameters
@app.get("/users/{user_id:int}")
async def get_user_by_id(user_id: int):
    return json_response({"user_id": user_id, "type": "int"})

# Float parameters
@app.get("/products/{price:float}")
async def products_by_price(price: float):
    return json_response({"max_price": price})

# UUID parameters
@app.get("/sessions/{session_id:uuid}")
async def get_session(session_id: uuid.UUID):
    return json_response({"session": str(session_id)})

# Multipath parameters (captures remaining path segments)
@app.get("/files/{filepath:multipath}")
async def serve_file(filepath: str):
    return json_response({"file": filepath})

# Multiple parameters
@app.get("/users/{user_id:int}/posts/{post_id:int}")
async def get_user_post(user_id: int, post_id: int):
    return json_response({"user_id": user_id, "post_id": post_id})
```

**Supported Parameter Types:**

- `{name}` or `{name:str}` - String (default)
- `{name:int}` - Integer (only matches numeric values)
- `{name:float}` - Float (matches decimal numbers)
- `{name:uuid}` - UUID (matches valid UUID format)
- `{name:multipath}` - Multipath (captures all remaining path segments)

**Multipath Parameter Matching:**

- `/files/{filepath:multipath}` matches `/files/doc.pdf` and `/files/folder/doc.pdf`
- The `filepath` parameter contains `doc.pdf` or `folder/doc.pdf` respectively
- Can capture empty paths: `/files/` results in `filepath = ""`

### Router Prefixes and Organization

Organize your application with modular routers and prefixes:

```python
from vira import Vira, APIRouter

app = Vira()

# Create routers with prefixes
api_router = APIRouter(prefix="/api/v1")
admin_router = APIRouter(prefix="/admin")
users_router = APIRouter()

# Define routes on specific routers
@api_router.get("/health")
async def api_health():
    return json_response({"status": "ok"})

@admin_router.get("/dashboard")
async def admin_dashboard():
    return json_response({"admin": True})

@users_router.get("/{user_id:int}")
async def get_user(user_id: int):
    return json_response({"user_id": user_id})

# Include routers with additional prefixes
app.include_router(api_router)                    # Routes: /api/v1/*
app.include_router(admin_router, prefix="/v2")    # Routes: /v2/admin/*
app.include_router(users_router, prefix="/api/users")  # Routes: /api/users/*

# Final route structure:
# GET /api/v1/health
# GET /v2/admin/dashboard
# GET /api/users/{user_id:int}
```

### Route Priority and Matching Order

Control route matching order with priority values (higher numbers = higher priority):

```python
# Specific routes should have higher priority than generic ones
@app.get("/users/me", priority=10)
async def current_user():
    return json_response({"current_user": True})

@app.get("/users/{user_id:int}", priority=5)
async def get_user_by_id(user_id: int):
    return json_response({"user_id": user_id})

@app.get("/users/{path:multipath}", priority=1)
async def users_catchall(path: str):
    return json_response({"path": path})

# Matching order: /users/me → /users/{user_id:int} → /users/{path:multipath}
```

### Nested Router Example

```python
# User management router
users_router = APIRouter(prefix="/users")

@users_router.get("/")
async def list_users():
    return json_response({"users": []})

@users_router.get("/{user_id:int}/profile")
async def user_profile(user_id: int):
    return json_response({"user_id": user_id, "profile": {}})

# Add posts routes directly to users router (not as nested router)
@users_router.get("/{user_id:int}/posts/{post_id:int}")
async def get_user_post(user_id: int, post_id: int):
    return json_response({"user_id": user_id, "post_id": post_id})

@users_router.post("/{user_id:int}/posts")
async def create_user_post(user_id: int):
    return json_response({"user_id": user_id, "message": "Post created"})

# Include users router in main app
app.include_router(users_router, prefix="/api")

# Final routes:
# GET  /api/users/
# GET  /api/users/{user_id:int}/profile
# GET  /api/users/{user_id:int}/posts/{post_id:int}
# POST /api/users/{user_id:int}/posts
```

### Performance Optimization

Vira includes automatic performance optimizations:

- **Segment Count Pre-filtering**: Routes are quickly filtered by path segment count before expensive regex matching
- **Priority-based Sorting**: Higher priority routes are checked first
- **Regex Compilation**: Path patterns are compiled once during route registration
- **Early Exit**: Matching stops at the first successful route

## Middleware System

Vira provides a powerful middleware system that allows you to add cross-cutting functionality to your application. Middleware executes in the same order as registration, allowing you to build a pipeline of request/response processing.

### Basic Middleware Usage

```python
from vira import Vira, text_response, json_response

app = Vira()

# Simple logging middleware
async def logging_middleware(request, call_next):
    print(f"Request: {request.method} {request.path}")
    response = await call_next(request)
    print(f"Response: {response.status_code}")
    return response

# Performance monitoring middleware
async def performance_middleware(request, call_next):
    import time
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    response.headers['X-Process-Time'] = str(duration)
    return response

# Register middleware (executes in registration order)
app.add_middleware(logging_middleware)
app.add_middleware(performance_middleware)

@app.get("/")
async def home(request):
    return text_response("Hello World!")
```

### Advanced Middleware Examples

```python
import json
import time
from typing import Dict, Any

# Request tracking middleware
async def request_tracking_middleware(request, call_next):
    # Add unique request ID
    request_id = f"req_{int(time.time() * 1000)}"
    request.state.request_id = request_id

    response = await call_next(request)
    response.headers['X-Request-ID'] = request_id
    return response

# Authentication middleware
async def api_key_middleware(request, call_next):
    # Skip auth for public endpoints
    if request.path.startswith('/public'):
        return await call_next(request)

    api_key = request.headers.get('X-API-Key')
    if not api_key or api_key != 'secret-key-123':
        return json_response(
            {"error": "Invalid or missing API key"},
            status_code=401
        )

    return await call_next(request)

# CORS middleware
async def cors_middleware(request, call_next):
    response = await call_next(request)
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-API-Key'
    return response

# Register all middleware
app.add_middleware(request_tracking_middleware)
app.add_middleware(api_key_middleware)
app.add_middleware(cors_middleware)
```

### Middleware Execution Order

Middleware executes in the **same order as registration**:

1. **Request Phase**: First registered → Last registered
2. **Response Phase**: Last registered → First registered

```python
# Registration order
app.add_middleware(middleware_a)  # 1st
app.add_middleware(middleware_b)  # 2nd
app.add_middleware(middleware_c)  # 3rd

# Execution flow for a request:
# Request: A → B → C → Route Handler
# Response: C → B → A → Client
```

### Error Handling in Middleware

```python
async def error_handling_middleware(request, call_next):
    try:
        response = await call_next(request)
        return response
    except ValueError as e:
        return json_response(
            {"error": "Invalid input", "detail": str(e)},
            status_code=400
        )
    except Exception as e:
        return json_response(
            {"error": "Internal server error"},
            status_code=500
        )
```

### Middleware State Management

Use `request.state` to share data between middleware and route handlers:

```python
async def auth_middleware(request, call_next):
    # Extract user info and store in request state
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    request.state.user = {"id": 1, "username": "john", "token": token}
    return await call_next(request)

@app.get("/profile")
async def get_profile(request):
    # Access user data from middleware
    user = request.state.user
    return json_response({"profile": user})
```

### Complete Middleware Example

See `examples/middleware_example.py` for a comprehensive real-world example with:

- Request tracking and unique IDs
- Performance monitoring with timing
- API key authentication
- Structured logging with request details
- CORS headers for browser compatibility

Run the example:

```bash
cd examples
uvicorn middleware_example:app --host 0.0.0.0 --port 8001 --reload
```

## Request Object API

### Basic Request Properties

```python
@app.post("/example")
async def handle_request(request):
    # HTTP method and path
    method = request.method          # "POST"
    path = request.path             # "/example"

    # Headers (case-insensitive)
    content_type = request.headers.get("content-type")
    user_agent = request.headers.get("User-Agent")

    # Request body (method call)
    body = request.body()           # bytes
    text = request.text()           # str

    # JSON parsing
    if body:
        data = json.loads(body.decode())

    return json_response({"received": "ok"})
```

### Path Parameters

```python
@app.get("/users/{user_id:int}/posts/{post_id:int}")
async def get_user_post(user_id: int, post_id: int):
    # Path parameters are automatically converted and injected as function parameters
    return json_response({
        "user_id": user_id,           # Already converted to int
        "post_id": post_id,           # Already converted to int
        "types": {
            "user_id": type(user_id).__name__,
            "post_id": type(post_id).__name__
        }
    })

# Alternative: Mix of parameter injection and request access
@app.get("/legacy/{item_id:int}")
async def legacy_route(request, item_id: int):
    # Can access via both methods, but parameter injection is preferred
    item_id_from_params = request.path_params["item_id"]  # Already converted to int
    assert item_id == item_id_from_params
    return json_response({"item_id": item_id})
```

### Query Parameters

```python
@app.get("/search")
async def search(request):
    # Single value query parameters
    query = request.query_params.get("q", "")
    limit = request.query_params.get("limit", "10")

    # Multi-value query parameters
    tags = request.query_params_multi.get("tags", [])  # List of all "tags" values

    # All query parameters
    all_params = dict(request.query_params)        # Single values only
    all_multi = request.query_params_multi         # All values as lists

    return json_response({
        "query": query,
        "tags": tags,
        "all_params": all_params
    })

# Example: /search?q=python&tags=web&tags=api&limit=20
# query = "python"
# tags = ["web", "api"]
# limit = "20"
```

### Cookies

```python
@app.get("/profile")
async def get_profile(request):
    # Read cookies
    user_id = request.cookies.get("user_id")
    theme = request.cookies.get("theme", "light")  # with default
    all_cookies = request.cookies  # Dict[str, str]

    if not user_id:
        return json_response({"error": "Not logged in"}, status_code=401)

    return json_response({"user_id": user_id, "theme": theme})
```

## Response Object API

### Response Types

```python
from vira import Response, text_response, html_response, json_response, redirect_response

@app.get("/examples")
async def response_examples(request):
    # Text response
    if request.path == "/text":
        return text_response("Plain text content")

    # HTML response
    elif request.path == "/html":
        return html_response("<h1>HTML Content</h1>")

    # JSON response
    elif request.path == "/json":
        return json_response({"message": "JSON data", "status": "ok"})

    # Redirect response
    elif request.path == "/redirect":
        return redirect_response("/")

    # Custom response
    else:
        return Response(
            "Custom response",
            status_code=200,
            headers={"X-Custom": "value"}
        )
```

### Cookie Management

```python
@app.post("/login")
async def login(request):
    body = request.body()
    data = json.loads(body.decode()) if body else {}

    # Validate credentials (simplified)
    if data.get("username") == "admin":
        # Set cookies with method chaining
        response = (json_response({"status": "logged in"})
                   .set_cookie("user_id", "12345", max_age=3600, httponly=True)
                   .set_cookie("session", "abc123", secure=True)
                   .set_cookie("theme", "dark", path="/"))
        return response
    else:
        return json_response({"error": "Invalid credentials"}, status_code=401)

@app.post("/logout")
async def logout(request):
    # Clear cookies
    response = (json_response({"status": "logged out"})
               .delete_cookie("user_id")
               .delete_cookie("session")
               .clear_cookies())  # Clear all cookies
    return response
```

### Full Cookie Attributes

```python
response.set_cookie(
    name="preferences",
    value="advanced_user",
    max_age=86400,              # 24 hours in seconds
    expires=datetime(2025, 12, 31),  # Explicit expiration date
    path="/admin",              # Cookie path
    domain="example.com",       # Cookie domain
    secure=True,                # HTTPS only
    httponly=True,              # Not accessible via JavaScript
    samesite="Strict"           # CSRF protection
)
```

## HTTP Methods Support

```python
app = Vira()

@app.get("/resource")
async def get_resource(request):
    return json_response({"method": "GET"})

@app.post("/resource")
async def create_resource(request):
    return json_response({"method": "POST"})

@app.put("/resource")
async def update_resource(request):
    return json_response({"method": "PUT"})

@app.delete("/resource")
async def delete_resource(request):
    return json_response({"method": "DELETE"})

@app.patch("/resource")
async def patch_resource(request):
    return json_response({"method": "PATCH"})

@app.head("/resource")
async def head_resource(request):
    return Response("", status_code=200)

@app.options("/resource")
async def options_resource(request):
    return Response("", headers={
        "Allow": "GET,POST,PUT,DELETE,PATCH,HEAD,OPTIONS"
    })
```

## Error Handling

Vira automatically handles common HTTP errors:

```python
# Automatic 404 for unmatched routes
# GET /nonexistent -> 404 Not Found

# Automatic 405 for wrong methods
# POST /api/users (when only GET is defined) -> 405 Method Not Allowed
# Includes proper "Allow" header with supported methods

# Manual error responses
@app.get("/error-example")
async def error_example(request):
    error_type = request.query_params.get("type", "400")

    if error_type == "400":
        return json_response({"error": "Bad Request"}, status_code=400)
    elif error_type == "500":
        return json_response({"error": "Internal Server Error"}, status_code=500)
    else:
        return json_response({"status": "ok"})
```

## Installation & Running

### Development Setup

```bash
# Clone or download the Vira framework
cd vira-project

# Install ASGI server (uvicorn recommended)
pip install uvicorn

# Create your application
# your_app.py
from vira import Vira, text_response

app = Vira()

@app.get("/")
async def home(request):
    return text_response("Hello, Vira!")

# Run the application
uvicorn your_app:app --reload --port 8000
```

### Production Deployment

```bash
# With multiple workers
uvicorn your_app:app --host 0.0.0.0 --port 8000 --workers 4

# With Hypercorn
pip install hypercorn
hypercorn your_app:app --bind 0.0.0.0:8000

# With Daphne
pip install daphne
daphne -b 0.0.0.0 -p 8000 your_app:app
```

## Lifespan Events

Vira supports ASGI lifespan events for managing application startup and shutdown tasks, similar to FastAPI. This allows you to run initialization code when your application starts and cleanup code when it shuts down.

### Basic Usage

```python
from vira import Vira
import asyncio

app = Vira()

# Startup events - run when the application starts
@app.on_event("startup")
async def connect_database():
    print("=> Connecting to database...")
    await asyncio.sleep(0.5)  # Simulate database connection
    print("=> Database connected!")

@app.on_event("startup")
async def load_configuration():
    print("=> Loading configuration...")
    app.state = type('State', (), {})()
    app.state.config_loaded = True
    print("=> Configuration loaded!")

# Shutdown events - run when the application stops
@app.on_event("shutdown")
async def cleanup():
    print("=> Cleaning up resources...")
    print("=> Cleanup completed!")

@app.get("/")
async def root(request):
    return {"message": "Hello from Vira with lifespan events!"}
```

### Alternative Registration Method

You can also register event handlers programmatically:

```python
async def initialize_cache():
    print("=> Initializing cache...")

async def close_connections():
    print("=> Closing connections...")

# Register handlers using method calls
app.add_event_handler("startup", initialize_cache)
app.add_event_handler("shutdown", close_connections)
```

### Multiple Handlers

You can register multiple handlers for the same event type. They execute in registration order:

```python
@app.on_event("startup")
async def setup_database():
    print("1. Setting up database...")

@app.on_event("startup")
async def setup_cache():
    print("2. Setting up cache...")

@app.on_event("startup")
async def setup_monitoring():
    print("3. Setting up monitoring...")

# Output when server starts:
# 1. Setting up database...
# 2. Setting up cache...
# 3. Setting up monitoring...
```

### Error Handling

- **Startup errors**: If a startup handler raises an exception, application startup fails
- **Shutdown errors**: Shutdown handler exceptions are logged but don't prevent other handlers from running

### Use Cases

Lifespan events are perfect for:

- Database connection setup and cleanup
- Loading ML models or configuration
- Setting up monitoring and logging
- Cache initialization
- Background task management

## Examples and Documentation

### Code Examples

See the `examples/` directory for complete examples:

- `routing_example.py` - Basic routing demonstration
- `advanced_routing_example.py` - Advanced routing with path parameters and nested routers
- `middleware_example.py` - Comprehensive middleware system with real-world patterns

### Complete Documentation

- `ROUTING_GUIDE.md` - Comprehensive guide to Vira's advanced routing system
- `MIDDLEWARE_GUIDE.md` - In-depth middleware architecture and implementation guide
- `ROADMAP.md` - Future development plans

## Architecture

Vira v0.3.0 uses a clean, modular architecture with advanced routing capabilities:

```
Vira Application
├── APIRouter (main router with prefix support)
│   ├── Route objects (path + handler + methods + priority)
│   │   ├── Path parameter extraction and type conversion
│   │   ├── Regex compilation and segment counting
│   │   └── Priority-based matching order
│   └── include_router() for nested sub-routers with prefixes
├── Request object (scope + body + path_params)
├── Response object (content + headers + cookies)
└── ASGI protocol implementation with automatic error handling
```

### Key Components

- **Vira**: Main application class with ASGI protocol implementation and automatic route registration
- **APIRouter**: Route collection with decorators, prefix-based inclusion, and nested router support
- **Route**: Individual route definition with path parameters, type conversion, priority, and optimized matching
- **Request**: High-level request object with path parameters, query parameters, cookies, and easy data access
- **Response**: High-level response object with automatic content type detection and cookie management

### Routing Engine Features

- **Path Parameter Types**: str, int, float, uuid, and path types with automatic conversion
- **Segment-Count Optimization**: Fast pre-filtering before regex matching for high performance
- **Priority System**: Explicit route priority with automatic sorting by specificity
- **Prefix Support**: Multiple levels of router nesting with prefix composition
- **Parameter Injection**: Automatic injection of converted path parameters into handler functions

## HTTP Status Codes

```python
from vira import HTTPStatus

# Common status codes
HTTPStatus.HTTP_200_OK                    # 200
HTTPStatus.HTTP_201_CREATED              # 201
HTTPStatus.HTTP_400_BAD_REQUEST          # 400
HTTPStatus.HTTP_401_UNAUTHORIZED         # 401
HTTPStatus.HTTP_404_NOT_FOUND           # 404
HTTPStatus.HTTP_405_METHOD_NOT_ALLOWED  # 405
HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR # 500

# Use in responses
return json_response(
    {"error": "Not found"},
    status_code=HTTPStatus.HTTP_404_NOT_FOUND
)
```

## Testing

```python
# Run the test suite
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_routing.py

# Test with coverage
pip install pytest-cov
python -m pytest tests/ --cov=vira
```

## Educational Purpose

Vira is designed for learning how modern web frameworks work at a fundamental level:

- **ASGI Protocol**: Understand async web server interfaces and application lifecycle
- **Advanced Routing**: Learn how URL patterns, regex compilation, and path parameters work
- **Type Conversion**: See how string URL segments become typed Python objects
- **Request/Response Cycle**: Understand how HTTP requests become Python objects and back
- **Performance Optimization**: Learn about segment-count filtering and route prioritization
- **Modular Architecture**: Understand how routers, prefixes, and nested inclusion work
- **Parameter Injection**: See how frameworks automatically inject dependencies
- **Cookie Management**: Understand HTTP cookie mechanics and security attributes
- **Content Negotiation**: Learn how content types and headers are handled

The codebase is intentionally simple, well-commented, and includes comprehensive tests to serve as a learning resource for understanding modern web framework internals.

## License

MIT License - see LICENSE file for details.

## Requirements

- Python 3.8+
- ASGI server (uvicorn, hypercorn, daphne)

Vira has no external dependencies - it's built using only Python standard library.

## Testing Vira Applications

When writing tests for Vira applications, especially those using middleware, you may need to manually build the middleware chain since tests don't go through the normal ASGI startup process.

### Testing with Middleware

```python
import pytest
from vira import Vira, text_response

@pytest.mark.asyncio
async def test_app_with_middleware():
    app = Vira()

    @app.middleware()
    async def add_header(request, call_next):
        response = await call_next(request)
        response.headers["X-Test"] = "middleware-applied"
        return response

    @app.get("/")
    async def home(request):
        return text_response("Hello World")

    # IMPORTANT: Build middleware chain before testing
    await app._build_middleware_chain()

    # Now test your application
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    sent_messages = []
    async def send(message):
        sent_messages.append(message)

    await app(scope, receive, send)

    # Verify middleware was applied
    response_start = next(msg for msg in sent_messages if msg["type"] == "http.response.start")
    headers = dict(response_start["headers"])
    assert b"x-test" in headers
```

### Why Manual Chain Building?

Vira optimizes performance by building the middleware chain once during application startup. In test environments, this startup process doesn't happen automatically, so you need to call `await app._build_middleware_chain()` manually after adding middleware but before making ASGI calls.

This ensures your tests accurately reflect the behavior of your application in production.
