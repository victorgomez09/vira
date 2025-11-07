# virapi Application Core

## Overview

The `virapi` class is the main entry point for the ASGI application. It serves as the framework's core, responsible for managing application lifecycle events (`startup`/`shutdown`), configuring global settings, building the middleware chain, and routing incoming requests.

## Key Components

| Component | Description |
| :--- | :--- |
| **`virapi`** (Class) | The ASGI callable object that implements the core application logic. |
| **`api_router`** | An instance of `APIRouter` used to manage all application routes. |
| **`middleware_chain`** | An instance of `MiddlewareChain` used to construct the request processing pipeline. |
| **`state`** | An instance of `State` used for application-level, thread-safe data storage. |

## How to Use

### 1. Initialization and Configuration

```python
from virapi import virapi

# Max file size in memory (before using disk) and temp directory can be configured
app = virapi(
    max_in_memory_file_size=2 * 1024 * 1024, # 2MB
    temp_dir="/tmp/vira_uploads"
)
```

### 2. Routing
Use the convenience decorators to define handlers.

```python
from virapi.request import Request
from virapi.response import json_response

@app.get("/")
async def homepage(request: Request):
    return json_response({"message": "Hello, virapi!"})

@app.post("/users")
async def create_user(request: Request):
    data = await request.json()
    return json_response({"id": 1, "username": data["name"]}, status_code=201)
```

### 3. Middleware, Plugins, and Events

```python
from virapi.middleware_chain import MiddlewareCallable
from virapi.plugin import ViraPlugin
import asyncio

# Add Middleware
async def log_middleware(request, call_next):
    print(f"Request: {request.path}")
    response = await call_next(request)
    print(f"Response Status: {response.status_code}")
    return response

app.add_middleware(log_middleware)

# Add Lifecycle Events
@app.on_event("startup")
async def init_db():
    print("Database connection pool initialized.")
    await asyncio.sleep(0.1)

@app.on_event("shutdown")
async def close_db():
    print("Database connection pool closed.")
```

## Implementation Notes
- ASGI Entry Point: The __call__ method handles both http and lifespan scopes.

- Request Cleanup: The http handling ensures request.cleanup_files() is called in a finally block, guaranteeing temporary file removal even if an exception occurs during the handler execution.

- Configuration Injection: The constructor sets application-wide configurations (like file size limits and temp dir) on the static attributes of the Request class.