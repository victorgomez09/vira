# Application State Management

## Overview

The `State` class provides a simple, thread-safe, in-process store for application-level data. It is primarily used to hold global resources, configurations, or counters that need to be shared across requests and components (like database connections or caches).

## Key Component

| Component | Description |
| :--- | :--- |
| **`State`** (Class) | A dictionary-like container for application data, protected by `threading.Lock` and `asyncio.Lock`. |

## How to Use

The state can be accessed via attribute access or dictionary-like methods.

### 1. Initialization and Access

The `State` object is typically initialized by the `Vira` application, but can be manually initialized.

```python
from vira.state import State

# Initialize with default data
app_state = State({"app_name": "Vira App", "is_ready": False})

# Attribute access (Synchronous)
print(app_state.app_name) # Output: Vira App

# Dictionary-like access (Synchronous)
app_state.set("counter", 0)
count = app_state.get("counter")
```

### 2. Synchronous Operations
The standard methods are thread-safe using threading.Lock.

```python
app_state.set("config", {"timeout": 10})
app_state.update({"is_ready": True, "version": "1.0"})
```

### 3. Asynchronous Operations
For use in async functions (like middleware or handlers), use the aset and aget methods, which use asyncio.Lock.

```python
import asyncio

async def update_state(state: State):
    # Use await on async methods
    current_count = await state.aget("async_counter", 0)
    await state.aset("async_counter", current_count + 1)

# Usage in a Vira lifecycle event
@app.on_event("startup")
async def on_startup():
    await app.state.aset("db_connection", "connection_object")
```

## Implementation Notes
- Dual Locking: It uses threading.Lock for synchronous attribute/method access and asyncio.Lock for asynchronous methods (aset/aget), ensuring safety in all contexts.

- Attribute Fallback: Attribute access (state.key) uses Python's __getattr__ and __setattr__ to redirect calls to the internal _data dictionary while preserving the ability to set internal attributes like _lock.

- Process Safety: The documentation explicitly warns that this class does not synchronize between multiple processes (e.g., when running with multiple worker processes under Gunicorn/Uvicorn), requiring an external store like Redis or a database for true cross-process state.