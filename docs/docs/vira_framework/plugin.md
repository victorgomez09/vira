# Vira Plugin Base

## Overview

The `ViraPlugin` class provides the base interface for extending the functionality of the core `Vira` application. It follows a simple pattern: initialization with a reference to the main application and a required `register()` method for setup logic.

## Key Component

| Component | Description |
| :--- | :--- |
| **`ViraPlugin`** (Class) | The abstract base class that all Vira extensions must inherit from. |
| **`self.app`** | A reference to the main `Vira` application instance, granting access to its state, router, and middleware chain. |
| **`register()`** | An abstract method that *must* be implemented by the subclass. This is where all setup (adding routes, middleware, or event handlers) should occur. |

## How to Use

### 1. Creating a Custom Plugin

Subclass `ViraPlugin` and implement the `register` method.

```python
from vira.plugin import ViraPlugin
from vira.response import json_response
from vira.request import Request

class HealthCheckPlugin(ViraPlugin):
    """Adds a /health route to the application."""

    def register(self):
        # Access the main router via self.app
        self.app.api_router.get("/health")(self.health_handler)

    async def health_handler(self, request: Request):
        # Access application state if needed
        is_ready = self.app.state.get("is_ready", False)

        if is_ready:
            return json_response({"status": "ok"}, status_code=200)
        else:
            return json_response({"status": "initializing"}, status_code=503)
```


### 2. Registering the Plugin
Register the plugin class (not an instance) with the main application.

```python
from vira import Vira
# ... HealthCheckPlugin defined above ...

app = Vira()
app.add_plugin(HealthCheckPlugin) 
# The plugin is now initialized and its register() method has been called.
```

## Implementation Notes
- Registration Timing: Plugins must be added before the application starts (before the middleware chain is built). An internal check ensures this.

- Dependency Injection: The Vira application is automatically passed to the plugin's __init__ method, giving the plugin full access to modify and extend the application instance.