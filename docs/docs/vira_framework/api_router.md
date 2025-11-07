# API Router

## Overview

The `APIRouter` class manages a collection of `Route` objects, organizing the application's URL structure. It is responsible for route prefixes, the route sorting mechanism, and efficiently finding the correct route handler for an incoming request path and method.

## Key Components

| Component | Description |
| :--- | :--- |
| **`APIRouter`** (Class) | Container for routes, providing the main routing logic. |
| **`prefix`** | A string prefix applied to all routes added to this router. |
| **`add_route(path, handler, methods, priority)`** | Manually registers a new route. Automatically sorts the routes. |
| **`route(path, methods, priority)`** | Decorator factory for route registration. |
| **`include_router(router, prefix)`** | Merges all routes from another `APIRouter` into the current one. |
| **`find_route(path, method)`** | The core matching function, returns the matching `Route` and extracted path parameters. |
| **Route Decorators** | `get()`, `post()`, `put()`, `delete()`, `patch()`, `head()`, `options()`. |

## How to Use

### 1. Basic Router Definition

```python
from virapi.routing import APIRouter
from virapi.response import text_response

user_router = APIRouter(prefix="/users")

@user_router.get("/")
async def list_users():
    return text_response("List of users")

@user_router.post("/")
async def create_user():
    return text_response("User created", status_code=201)
```

### 2. Router Inclusion in Main App

```python
from virapi import virapi
# ... user_router defined above ...

app = virapi()
app.include_router(user_router) # Routes become accessible at /users and /users/
```

### 3. Route Specificity and Priority
Routes are automatically sorted using a specificity score. This ensures that more precise paths are checked before more generic ones, preventing a generic route like /{name} from intercepting a specific route like /admin.

The sorting key is a tuple: (priority, literal_segments, total_segments, -definition_order).

priority: Manually assigned (higher value = higher priority).

literal_segments: Number of fixed path parts (e.g., /api/v1 has 2).

total_segments: Total path parts (literal + dynamic).

```python
# Route 1 (Most specific due to literal segments)
@router.get("/users/me") # Specificity wins
async def get_me(): ...

# Route 2 (Less specific, dynamic segment)
@router.get("/users/{user_id:int}") # Checked after /users/me
async def get_user(user_id: int): ...
```

## Implementation Details
- Sorting: Routes are sorted immediately after add_route or include_router is called to maintain the correct matching .order.

- Error Handling: If find_route finds a path match but the method is not allowed, the handle_request method automatically returns a 405 Method Not Allowed response. If no path is found, it returns 404 Not Found.