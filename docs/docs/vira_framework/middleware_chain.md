# Middleware Chain Manager

## Overview

The `MiddlewareChain` class is responsible for managing a list of middleware functions and building the final request execution pipeline. It enforces the **"onion" pattern**, where each middleware wraps the next, ensuring the first-registered middleware is the outermost (executed first and last).

## Key Components

| Component | Description |
| :--- | :--- |
| **`MiddlewareChain`** (Class) | Manages the collection of middleware and builds the executable chain. |
| **`MiddlewareCallable`** (Protocol) | Defines the required signature for all middleware: `async def (request, call_next) -> Response`. |
| **`add(middleware)`** | Registers a new middleware function to the chain. |
| **`build(endpoint)`** | Constructs the final, nested callable by wrapping the final route `endpoint` with all registered middleware. |

## How to Use

### 1. Defining a Middleware

A middleware is an async function that accepts a `request` and an async `call_next` function.

```python
from vira.request import Request
from vira.response import Response

async def timer_middleware(request: Request, call_next):
    # 1. Pre-process logic (before the next handler is called)
    start_time = time.time()
    
    # 2. Call the next middleware or the final route handler
    response = await call_next(request)
    
    # 3. Post-process logic (after the next handler returns)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = f"{process_time:.4f}s"
    
    return response


### 2. Building the Chain
The main Vira application handles the building process internally, but here's how the logic works:

```python
from vira.middleware_chain import MiddlewareChain
from vira.response import text_response

async def final_handler(request):
    return text_response("Endpoint hit")

chain = MiddlewareChain()
chain.add(middleware_A)
chain.add(middleware_B)
chain.add(final_handler)

# The built_app is now a callable: middleware_A(middleware_B(final_handler))
built_app = chain.build(final_handler)
```

## Implementation Details
- Onion Pattern: When building, the method iterates over registered middleware in reverse order. This ensures that the closure captures the correct next_handler, creating the nested structure.

- Closure: Inside the build method, a new middleware_handler function is created for each middleware. This handler defines the call_next function, which is a closure over the specific next_app (the next element in the chain) for that stage.