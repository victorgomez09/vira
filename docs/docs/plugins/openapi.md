# Vira OpenAPI Plugin (API Documentation)

The `ViraOpenAPIPlugin` automatically generates the **OpenAPI (Swagger)** specification for your application's routes and serves the interactive documentation user interface.

## 1. Installation and Configuration

The plugin introspects your application's `api_router` to gather all route information.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`title`** | `str` | `"Vira API"` | The main title of your documentation site. |
| **`version`** | `str` | `"1.0.0"` | The version of the API. |
| **`openapi_path`** | `str` | `"/openapi.json"` | The endpoint serving the raw OpenAPI JSON specification. |
| **`docs_path`** | `str` | `"/docs"` | The endpoint serving the interactive **Swagger UI**. |

### Example Registration

```python
# app.py

from vira import Vira
from plugins.openapi.openapi import ViraOpenAPIPlugin
from vira.response import json_response

app = Vira()

# 1. Register the plugin
app.add_plugin(
    ViraOpenAPIPlugin,
    title="Core Vira Microservice",
    version="1.5.0",
)

# 2. Define your routes as normal (The plugin finds them)
@app.get("/health")
async def health_check():
    """
    Checks the service health and status.
    ---
    tags: [System]
    """
    return json_response({"status": "ok"})
```

## 2. Accessing the Docs
Once the plugin is registered, two endpoints become available automatically:

| Endpoint | Content |
| :--- | :--- |
| [base_url]/openapi.json | The raw OpenAPI 3.0 JSON specification. |
| [base_url]/docs | The interactive Swagger UI (web interface). |


## 3. Schema Generation
The plugin generates documentation based on the following rules:

- Route Information: HTTP method, path, and path parameters (e.g., {id:int}) are automatically mapped.

- Descriptions: The docstrings of your route handler functions are used for the operation summary and description.

- Pydantic Integration: If you have Pydantic installed, the plugin will automatically use models in your function type hints to generate detailed JSON Schemas for request bodies and response types.