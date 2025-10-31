# Vira Lifespan Events Guide

Vira supports ASGI lifespan events for managing application startup and shutdown tasks, similar to FastAPI. This allows you to run initialization code when your application starts and cleanup code when it shuts down.

## Overview

Lifespan events are useful for:
- Database connection setup and cleanup
- Loading configuration or ML models
- Setting up monitoring and logging
- Cache initialization
- Background task management

## Usage

### 1. Using the `@app.on_event()` Decorator

```python
from vira import Vira

app = Vira()

@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print("Application starting up!")
    # Initialize database, load config, etc.

@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("Application shutting down!")
    # Close connections, save state, etc.
```

### 2. Using `app.add_event_handler()`

```python
async def initialize_database():
    print("Connecting to database...")
    # Database setup code here

async def close_database():
    print("Closing database connection...")
    # Database cleanup code here

# Register handlers
app.add_event_handler("startup", initialize_database)
app.add_event_handler("shutdown", close_database)
```

## Event Types

### Startup Events

Startup events run when the ASGI server starts your application, before any HTTP requests are processed.

```python
@app.on_event("startup")
async def startup():
    # This runs once when the server starts
    app.state.database = await connect_to_database()
    app.state.ml_model = load_machine_learning_model()
```

### Shutdown Events

Shutdown events run when the ASGI server is shutting down your application.

```python
@app.on_event("shutdown")
async def shutdown():
    # This runs once when the server shuts down
    await app.state.database.close()
    save_application_metrics()
```

## Multiple Event Handlers

You can register multiple handlers for the same event type. They will be executed in the order they were registered:

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

## Error Handling

If a startup event handler raises an exception, the application startup will fail:

```python
@app.on_event("startup")
async def failing_startup():
    raise RuntimeError("Database connection failed")
    # This will prevent the application from starting
```

If a shutdown event handler raises an exception, it will be logged but won't prevent other shutdown handlers from running:

```python
@app.on_event("shutdown")
async def failing_shutdown():
    raise RuntimeError("Error during cleanup")
    # Other shutdown handlers will still run
```

## Complete Example

```python
import asyncio
import time
from vira import Vira
from vira.response import json_response

app = Vira()

# Application state
app.state = type('State', (), {})()

@app.on_event("startup")
async def startup():
    print("=> Initializing application...")
    app.state.start_time = time.time()
    app.state.database = await simulate_database_connection()
    print("=> Application ready!")

@app.on_event("shutdown")
async def shutdown():
    print("=> Shutting down application...")
    uptime = time.time() - app.state.start_time
    print(f"=> Application ran for {uptime:.2f} seconds")
    await app.state.database.close()
    print("=> Shutdown complete!")

async def simulate_database_connection():
    await asyncio.sleep(0.1)  # Simulate connection time
    return type('Database', (), {'close': lambda: None})()

@app.get("/")
async def root(request):
    uptime = time.time() - app.state.start_time
    return json_response({
        "message": "Hello from Vira!",
        "uptime_seconds": uptime
    })
```

## Running with Uvicorn

When you run your Vira application with uvicorn, the lifespan events will be automatically triggered:

```bash
uvicorn main:app --reload
```

Output:
```
=> Initializing application...
=> Application ready!
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

When you stop the server (Ctrl+C):
```
=> Shutting down application...
=> Application ran for 45.23 seconds
=> Shutdown complete!
INFO:     Shutting down
```

## ASGI Lifespan Protocol

Vira implements the [ASGI Lifespan Protocol](https://asgi.readthedocs.io/en/latest/specs/lifespan.html) specification. This means:

1. The ASGI server sends a `lifespan.startup` message when the application should start
2. Vira runs all startup handlers and responds with `lifespan.startup.complete`
3. HTTP requests are processed normally
4. The ASGI server sends a `lifespan.shutdown` message when the application should stop
5. Vira runs all shutdown handlers and responds with `lifespan.shutdown.complete`

## Best Practices

1. **Keep startup fast**: Avoid long-running operations in startup handlers
2. **Handle errors gracefully**: Use try/except in handlers to prevent startup failures
3. **Order matters**: Register handlers in the order you want them to execute
4. **Use async**: Always make event handlers async functions
5. **Store state**: Use `app.state` or a similar pattern to store shared application state

## Testing Lifespan Events

You can test lifespan events directly:

```python
import asyncio
from your_app import app

async def test_startup():
    await app._run_startup_handlers()
    # Assert your startup conditions

async def test_shutdown():
    await app._run_shutdown_handlers()
    # Assert your cleanup conditions

# Run tests
asyncio.run(test_startup())
asyncio.run(test_shutdown())
```

## Comparison with FastAPI

Vira's lifespan events work similarly to FastAPI:

| Feature | Vira | FastAPI |
|---------|----------|---------|
| `@app.on_event("startup")` | ✅ | ✅ |
| `@app.on_event("shutdown")` | ✅ | ✅ |
| `app.add_event_handler()` | ✅ | ✅ |
| Multiple handlers | ✅ | ✅ |
| Error handling | ✅ | ✅ |
| ASGI lifespan protocol | ✅ | ✅ |

This makes it easy to migrate between Vira and FastAPI applications.

## Internal Startup Handlers

Vira automatically registers some internal startup handlers:

### Middleware Chain Building

The middleware chain building is automatically registered as the first startup handler. This ensures that:

1. **Performance Optimization**: The middleware chain is built once during startup, not on every request
2. **Consistent Behavior**: All middleware is properly configured before the first HTTP request
3. **Error Handling**: Any middleware configuration errors are caught during startup

```python
# This happens automatically - no user action required
app = Vira()

@app.middleware()
async def my_middleware(request, call_next):
    return await call_next(request)

# Middleware chain will be built during startup event
```

### Testing Considerations

In test environments where the ASGI lifespan events don't trigger automatically, you may need to manually build the middleware chain:

```python
# In tests only
await app._build_middleware_chain()
```

This ensures your tests behave consistently with production deployments.
