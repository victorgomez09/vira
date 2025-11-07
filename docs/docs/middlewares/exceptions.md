# Exceptions Middleware

## Overview

The `ExceptionMiddleware` serves as a universal safety net, catching any unhandled exceptions (like `ValueError`, `KeyError`, or generic `Exception`) raised by downstream middleware or your route handlers. It converts these failures into a standardized **JSON response** with a `500 Internal Server Error` status code.

## Initialization & Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`mode`** | `Literal["production", "debug"]` | `"production"` | Controls the verbosity of the error response. |

### Output Control by Mode

| Mode | JSON Response Detail | Use Case |
| :--- | :--- | :--- |
| **`"production"`** | Minimal information: `{"error": {"type": "HTTP_500_INTERNAL_SERVER_ERROR", "message": "Internal Server Error"}}`. | Safe for live environments; hides internal details from clients. |
| **`"debug"`** | Full traceback, exception type, and message are included. | Use only in development or staging for easier debugging. |

## Usage Example

```python
from virapi import virapi
from virapi.middleware.exception import ExceptionMiddleware

app = virapi()

# Recommended for development to see tracebacks
app.add_middleware(ExceptionMiddleware(mode="debug"))

# Recommended for production to hide internal details
# app.add_middleware(ExceptionMiddleware(mode="production")) 

# Example Handler that raises an unhandled exception
@app.get("/error")
async def trigger_error():
    # This will be caught by the middleware
    raise ValueError("Something went terribly wrong!")
```

## Implementation Notes
- Catch-All: This middleware explicitly catches all Exception types (except Exception as exc) to ensure a proper HTTP response is always sent, preventing the ASGI server from crashing.

- Placement: It should typically be placed at the beginning of the middleware chain (i.e., added first to app.add_middleware) to wrap all other components.