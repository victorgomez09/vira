# Vira Routing Guide

> **Complete Documentation**: This guide contains comprehensive documentation for all of Vira's routing features. For a quick overview, see the routing sections in `README.md`.

A comprehensive guide to Vira's advanced routing system including path parameters, type conversion, priority routing, and modular organization.

## Overview

Vira provides a powerful routing system inspired by FastAPI with the following key features:

- **Path Parameters**: Dynamic routes with automatic type conversion (int, str, float, uuid, path)
- **Type Safety**: Automatic parameter conversion and injection into handler functions
- **Modular Organization**: APIRouter with prefix support and nested inclusion
- **Priority Routing**: Control route matching order with explicit priorities
- **High Performance**: Optimized matching with segment-count pre-filtering
- **FastAPI-Style**: Familiar decorator-based route registration

## Path Parameters and Type Conversion

### Basic Path Parameters

Define dynamic routes that capture URL segments as parameters:

```python
from vira import Vira
import uuid

app = Vira()

# String parameters (default type)
@app.get("/users/{username}")
async def get_user_by_name(username: str):
    return {"user": username, "type": type(username).__name__}

# Explicit string type
@app.get("/categories/{category:str}")
async def get_category(category: str):
    return {"category": category}
```

### Supported Parameter Types

Vira supports five parameter types with automatic conversion:

#### 1. String Parameters (`str`)

```python
# Default type (no type specifier needed)
@app.get("/users/{username}")
async def get_user(username: str):
    return {"username": username}

# Explicit string type
@app.get("/tags/{tag:str}")
async def get_tag(tag: str):
    return {"tag": tag}
```

#### 2. Integer Parameters (`int`)

```python
@app.get("/users/{user_id:int}")
async def get_user_by_id(user_id: int):
    return {"user_id": user_id, "type": "integer"}

# Only matches numeric values
# /users/123 ✅ matches
# /users/abc ❌ no match
```

#### 3. Float Parameters (`float`)

```python
@app.get("/products/{price:float}")
async def products_by_price(price: float):
    return {"max_price": price}

# Matches decimal numbers
# /products/19.99 ✅ matches
# /products/20 ✅ matches (converted to 20.0)
# /products/abc ❌ no match
```

#### 4. UUID Parameters (`uuid`)

```python
@app.get("/sessions/{session_id:uuid}")
async def get_session(session_id: uuid.UUID):
    return {"session": str(session_id)}

# Only matches valid UUID format
# /sessions/550e8400-e29b-41d4-a716-446655440000 ✅ matches
# /sessions/invalid-uuid ❌ no match
```

#### 5. Multipath Parameters (`multipath`)

```python
@app.get("/files/{filepath:multipath}")
async def serve_file(filepath: str):
    return {"file": filepath}

# Captures remaining path segments
# /files/doc.pdf → filepath = "doc.pdf"
# /files/folder/doc.pdf → filepath = "folder/doc.pdf"
# /files/ → filepath = ""
```

### Multiple Parameters

Combine multiple path parameters in a single route:

```python
@app.get("/users/{user_id:int}/posts/{post_id:int}")
async def get_user_post(user_id: int, post_id: int):
    return {
        "user_id": user_id,
        "post_id": post_id,
        "message": f"Post {post_id} by user {user_id}"
    }

@app.get("/api/{version:str}/users/{user_id:int}")
async def get_versioned_user(version: str, user_id: int):
    return {"version": version, "user_id": user_id}
```

### Parameter Injection vs Request Access

Vira offers two ways to access path parameters:

#### 1. Parameter Injection (Recommended)

```python
@app.get("/users/{user_id:int}")
async def get_user(user_id: int):
    # Parameters are automatically converted and injected
    return {"user_id": user_id}
```

#### 2. Request Object Access

```python
@app.get("/users/{user_id:int}")
async def get_user(request):
    # Access via request.path_params (already converted)
    user_id = request.path_params["user_id"]
    return {"user_id": user_id}
```

## Modular Routing with APIRouter

### Basic Router Usage

Organize your application with modular routers:

```python
from vira import Vira, APIRouter

app = Vira()

# Create a router for user-related routes
users_router = APIRouter()

@users_router.get("/")
async def list_users():
    return {"users": []}

@users_router.get("/{user_id:int}")
async def get_user(user_id: int):
    return {"user_id": user_id}

@users_router.post("/")
async def create_user():
    return {"message": "User created"}

# Include router with prefix
app.include_router(users_router, prefix="/users")

# Routes become:
# GET /users/
# GET /users/{user_id:int}
# POST /users/
```

### Router Prefixes

Routers support prefixes at both construction and inclusion:

```python
# Prefix at construction
api_router = APIRouter(prefix="/api")

@api_router.get("/health")
async def health():
    return {"status": "ok"}

# Additional prefix at inclusion
app.include_router(api_router, prefix="/v1")
# Final route: GET /v1/api/health
```

### Nested Routers

Create complex route hierarchies with nested routers:

```python
# Main API router
api_router = APIRouter(prefix="/api")

# Users router
users_router = APIRouter()

@users_router.get("/")
async def list_users():
    return {"users": []}

@users_router.get("/{user_id:int}/profile")
async def user_profile(user_id: int):
    return {"user_id": user_id, "profile": {}}

# Posts router (to be nested under users)
posts_router = APIRouter()

@posts_router.get("/{post_id:int}")
async def get_post(post_id: int):
    return {"post_id": post_id}

@posts_router.get("/")
async def list_posts():
    return {"posts": []}

# Nest posts under users
users_router.include_router(posts_router, prefix="/{user_id:int}/posts")

# Include users in API
api_router.include_router(users_router, prefix="/users")

# Include API in main app
app.include_router(api_router, prefix="/v1")

# Final route structure:
# GET /v1/api/users/
# GET /v1/api/users/{user_id:int}/profile
# GET /v1/api/users/{user_id:int}/posts/
# GET /v1/api/users/{user_id:int}/posts/{post_id:int}
```

## Route Priority and Matching Order

### Priority System

Control route matching order with explicit priorities (higher numbers = higher priority):

```python
# Specific routes should have higher priority
@app.get("/users/me", priority=10)
async def current_user():
    return {"current_user": True}

@app.get("/users/admin", priority=10)
async def admin_user():
    return {"admin": True}

@app.get("/users/{user_id:int}", priority=5)
async def get_user_by_id(user_id: int):
    return {"user_id": user_id}

@app.get("/users/{username:str}", priority=3)
async def get_user_by_name(username: str):
    return {"username": username}

@app.get("/users/{path:multipath}", priority=1)
async def users_catchall(path: str):
    return {"path": path}

# Matching order for /users/me:
# 1. /users/me (priority=10) ✅ matches
# 2. Other routes not checked

# Matching order for /users/123:
# 1. /users/me (priority=10) ❌ no match
# 2. /users/admin (priority=10) ❌ no match
# 3. /users/{user_id:int} (priority=5) ✅ matches
```

### Automatic Priority Assignment

Routes without explicit priority are automatically sorted by specificity:

```python
# These routes are automatically ordered by specificity
@app.get("/users/special/action")  # Most specific
async def special_action():
    return {"action": "special"}

@app.get("/users/{user_id:int}/action")  # Medium specific
async def user_action(user_id: int):
    return {"user_id": user_id, "action": True}

@app.get("/users/{path:multipath}")  # Least specific
async def users_catchall(path: str):
    return {"path": path}
```

## Performance Optimization

Vira includes several performance optimizations for route matching:

### Segment Count Pre-filtering

Routes are quickly filtered by path segment count before expensive regex matching:

```python
# Fast rejection based on segment counts
# Route: /users/{user_id:int}  (2 segments)
# Request: /api/users/123/posts  (4 segments)
# Result: Quickly rejected without regex matching

# Route: /files/{filepath:multipath}  (2 segments, has multipath parameter)
# Request: /files/folder/doc.pdf  (3 segments)
# Result: Allowed to proceed to regex matching
```

### Route Sorting

Routes are automatically sorted for optimal performance:

1. By priority (higher first)
2. By specificity (more specific first)
3. By segment count (fewer segments first for non-path routes)

### Regex Compilation

Path patterns are compiled once during route registration, not during matching.

## Advanced Examples

### Complex Application Structure

```python
from vira import Vira, APIRouter
import uuid

app = Vira()

# API versioning
v1_router = APIRouter(prefix="/api/v1")
v2_router = APIRouter(prefix="/api/v2")

# Admin routes with high priority
admin_router = APIRouter(prefix="/admin")

@admin_router.get("/dashboard", priority=20)
async def admin_dashboard():
    return {"admin": "dashboard"}

@admin_router.get("/{section:str}", priority=15)
async def admin_section(section: str):
    return {"admin_section": section}

# User management
users_router = APIRouter()

@users_router.get("/me", priority=10)
async def current_user():
    return {"current": True}

@users_router.get("/{user_id:int}")
async def get_user(user_id: int):
    return {"user_id": user_id}

@users_router.get("/{user_id:int}/posts/{post_id:uuid}")
async def get_user_post(user_id: int, post_id: uuid.UUID):
    return {"user_id": user_id, "post_id": str(post_id)}

# File serving with path parameters
@app.get("/static/{filepath:multipath}")
async def serve_static(filepath: str):
    return {"file": filepath}

# Health checks with specific priority
@app.get("/health", priority=15)
async def health():
    return {"status": "healthy"}

# Include all routers
v1_router.include_router(users_router, prefix="/users")
v1_router.include_router(admin_router)

app.include_router(v1_router)
app.include_router(v2_router)

# Final route structure:
# GET /health (priority=15)
# GET /static/{filepath:multipath}
# GET /api/v1/admin/dashboard (priority=20)
# GET /api/v1/admin/{section:str} (priority=15)
# GET /api/v1/users/me (priority=10)
# GET /api/v1/users/{user_id:int}
# GET /api/v1/users/{user_id:int}/posts/{post_id:uuid}
```

### Type Validation Example

```python
@app.get("/validate/{number:int}/{decimal:float}/{id:uuid}")
async def validate_types(number: int, decimal: float, id: uuid.UUID):
    return {
        "number": number,
        "number_type": type(number).__name__,
        "decimal": decimal,
        "decimal_type": type(decimal).__name__,
        "id": str(id),
        "id_type": type(id).__name__
    }

# Example requests:
# GET /validate/42/3.14/550e8400-e29b-41d4-a716-446655440000
# Returns: {
#   "number": 42,
#   "number_type": "int",
#   "decimal": 3.14,
#   "decimal_type": "float",
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "id_type": "UUID"
# }
```

## Migration Guide

If you're upgrading from basic string-based routing to the advanced system:

### Before (Basic Routing)

```python
@app.get("/users/{user_id}")
async def get_user(request):
    user_id = request.path_params.get("user_id")
    # Manual conversion required
    try:
        user_id = int(user_id)
    except ValueError:
        return {"error": "Invalid user ID"}

    return {"user_id": user_id}
```

### After (Advanced Routing)

```python
@app.get("/users/{user_id:int}")
async def get_user(user_id: int):
    # Automatic conversion and injection
    return {"user_id": user_id}
```

## Best Practices

1. **Use Type Annotations**: Always annotate handler parameters for clarity
2. **Set Priorities Explicitly**: For overlapping routes, set explicit priorities
3. **Organize with Routers**: Use APIRouter for logical grouping
4. **Specific Before Generic**: Place specific routes before catch-all routes
5. **Use Multipath Parameters**: Prefer `{path:multipath}` over catch-all patterns
6. **Validate Parameters**: Let the framework handle type validation automatically

## Error Handling

Vira automatically handles routing errors:

- **404 Not Found**: When no route matches the request path
- **405 Method Not Allowed**: When route matches but method doesn't
- **400 Bad Request**: When path parameter type conversion fails

```python
# These requests will be handled automatically:
# GET /users/abc (where route expects {user_id:int}) → 404 Not Found
# POST /users/123 (where only GET is defined) → 405 Method Not Allowed
```
