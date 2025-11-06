# Single Route

## Overview

The `Route` class represents a single API endpoint. Its core responsibilities are parsing the path pattern into a regular expression, matching incoming URLs, converting dynamic path and query parameters to the correct Python types, and injecting them into the user's handler function.

## Key Components

| Component | Description |
| :--- | :--- |
| **`Route`** (Class) | Defines a single route with its handler and matching logic. |
| **`path`** | The URL pattern (e.g., `/users/{id:int}`). |
| **`route_regex`** | The compiled regular expression for efficient path matching. |
| **`param_types`** | Dictionary mapping parameter names to their expected Python types (`int`, `str`, etc.). |
| **`matches(path, method)`** | Checks if the given path and method match the route's definition. Returns path parameters. |
| **`handle(request)`** | Executes the route's handler function with automatic parameter injection. |

## How to Use (Parameter Injection)

The `handle` method uses Python's `inspect` module to automatically resolve and inject arguments based on type hints and parameter names.

### 1. Path Parameters

The type must be defined in the route path (e.g., `{user_id:int}`).

| Path Type | Python Type | Description |
| :--- | :--- | :--- |
| **`{name:str}`** | `str` | Matches any string (default). |
| **`{id:int}`** | `int` | Matches a sequence of digits and converts to `int`. |
| **`{val:float}`** | `float` | Matches a number with or without a decimal point. |
| **`{uid:uuid}`** | `uuid.UUID` | Matches a standard UUID string. |
| **`{filepath:multipath}`** | `str` | Matches the rest of the path, including slashes. |

```python
from vira.route import Route
from vira.response import json_response
from vira.request import Request

async def user_handler(user_id: int, request: Request):
    # user_id is automatically converted from str URL segment to int
    return json_response({"user_id": user_id})

# A Route object is created internally by the router
route = Route("/users/{user_id:int}", user_handler, {"GET"})


### 2. Query Parameters
Query string parameters are injected based on the handler's signature.

```python
# URL: /search?q=query&limit=10

async def search_handler(q: str, limit: int = 20, is_active: bool = False):
    # q (str) is required
    # limit (int) is converted and defaults to 20 if missing
    # is_active (bool) will be True if 'is_active' is present in query, False otherwise
    return json_response({"query": q, "limit": limit, "active": is_active})
```

## Implementation Notes
- Type Unwrapping: The internal _unwrap_type method handles standard library generic types like Union[int, None] (for Optional) to correctly identify the target type for conversion.

- Path Compilation: The path pattern is converted into a regular expression using Python's re module, with named capture groups for the dynamic parameters.