import inspect
import re
import json
from typing import Any, Callable, Dict, Optional, Type, get_type_hints, TYPE_CHECKING

# Define BaseModel type for static type checkers like Pylance/Mypy
# This block is only processed by the type checker, not at runtime, preventing ImportError
if TYPE_CHECKING:
    from pydantic import BaseModel as BASE_MODEL

# --- PYDANTIC DETECTION LOGIC (Integrated) ---
try:
    # If Pydantic is installed (the user used virapi[validation]), the real ones are imported.
    from pydantic import BaseModel as BASE_MODEL

    # Ensure the schema method exists for the documentation process
    if not hasattr(BASE_MODEL, "model_json_schema"):
        # This handles the case of Pydantic V1 (where it is .schema())
        # For V2 we use model_json_schema()
        # Note: In Pydantic V2, the schema() method was removed/replaced.
        # This line is an attempt at compatibility, but the ideal is to require Pydantic V2+.
        BASE_MODEL.model_json_schema = (
            BASE_MODEL.model_json_schema
            if hasattr(BASE_MODEL, "model_json_schema")
            else BASE_MODEL.schema
        )

    PYDANTIC_AVAILABLE = True
except ImportError:
    # If Pydantic is not installed, we create a dummy class
    class BaseModelDummy:
        """Dummy class that simulates BaseModel if Pydantic is not available."""

        @classmethod
        def model_json_schema(cls, *args, **kwargs):
            # Returns an empty schema to prevent documentation generation errors
            return {}

    BASE_MODEL = BaseModelDummy
    PYDANTIC_AVAILABLE = False
    print("virapi: Pydantic not detected. OpenAPI Request Body generation is disabled.")
# ---------------------------------------------------------------------------

# Note: I assume that the ViraPlugin, Response, and virapi classes are defined in other files
# and are importable (original imports are maintained for integrity).
from virapi.plugin import ViraPlugin
from virapi.response import Response
from virapi import Virapi


class OpenAPIDocs:
    """
    Class to generate the OpenAPI schema from virapi routes,
    including Pydantic support (using the BASE_MODEL alias).
    """

    def __init__(
        self,
        app: "Virapi",
        title: str = "Virapi API",
        description: str = "",
        version: str = "0.1.0",
    ):
        self.app = app
        self.title = title
        self.description = description
        self.version = version
        self._schema: Dict[str, Any] = {}
        # Keeps a record of Pydantic models (using BASE_MODEL) already added to avoid duplicates
        # FIX: Removed quotes, relying on the TYPE_CHECKING block for type inference.
        # Added # type: ignore to prevent Pylance warning due to conditional definition of BASE_MODEL.
        self._registered_schemas: Dict[str, Type[BASE_MODEL]] = {}  # type: ignore

    def generate_schema(self) -> Dict[str, Any]:
        """Generates and returns the complete OpenAPI schema (JSON/Dict)."""

        # Generates the base OpenAPI schema dictionary
        self._schema = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": (
                    self.description
                    if self.description
                    else f"{self.title} API documentation"
                ),
            },
            "paths": self._generate_paths(),
            "components": {"schemas": {}},
        }

        # After generating paths, we dump the registered Pydantic schemas
        # This call is safe because the BASE_MODEL class (real or dummy) has implemented
        # model_json_schema() to return {} if Pydantic is not available.
        if PYDANTIC_AVAILABLE:
            for name, model in self._registered_schemas.items():
                self._schema["components"]["schemas"][name] = model.model_json_schema()

        return self._schema

    def _add_pydantic_schema(self, model: Type[BASE_MODEL]):  # type: ignore
        """Registers a Pydantic model for inclusion in components/schemas."""
        model_name = model.__name__
        if model_name not in self._registered_schemas:
            self._registered_schemas[model_name] = model
            # In a real system, we would recursively inspect fields for nested models here

    def _get_openapi_type(self, type_hint: Type) -> str:
        """Maps Python/Pydantic types to basic OpenAPI types."""
        if type_hint is str:
            return "string"
        if type_hint is int:
            return "integer"
        if type_hint is float:
            return "number"
        if type_hint is bool:
            return "boolean"
        # Simple handling for other common Pydantic types
        if hasattr(type_hint, "__name__") and type_hint.__name__.lower() == "decimal":
            return "number"
        return "string"  # Default

    def _generate_paths(self) -> Dict[str, Any]:
        """
        Iterates over the list of routes in APIRouter and generates the 'paths' object.
        """
        paths = {}
        EXCLUDED_PATHS = {"/docs", "/openapi.json"}

        routes_list = getattr(self.app.api_router, "routes", None)

        if not isinstance(routes_list, list):
            print(
                "WARNING: 'routes' list not found in self.app.api_router. Route documentation will not be generated."
            )
            return {}

        for route in routes_list:
            path_pattern = route.path
            handler = route.handler

            if path_pattern in EXCLUDED_PATHS:
                continue

            # STEP 1: CONVERT VIRA PATH TO OPENAPI PATH
            # Assuming virapi's format is {name:type}
            openapi_path = re.sub(
                r"\{([a-zA-Z0-9_]+):[a-zA-Z]+\}", r"{\1}", path_pattern
            )

            if openapi_path not in paths:
                paths[openapi_path] = {}

            # route.methods is a Set[str] of the allowed methods for this route
            for method in route.methods:
                if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
                    operation = self._generate_operation(
                        method, openapi_path, handler, path_pattern
                    )
                    paths[openapi_path][method.lower()] = operation

        return paths

    def _generate_operation(
        self, method: str, path: str, handler: Callable, original_path: str
    ) -> Dict[str, Any]:
        """Generates the 'operation' object (GET, POST, etc.) for a specific route, including Pydantic."""

        docstring = handler.__doc__.strip() if handler.__doc__ else ""
        summary = docstring.split("\n")[0]
        description = docstring

        operation: Dict[str, Any] = {
            "summary": summary or f"{method} {path}",
            "description": description,
            "tags": ["API"],
            "parameters": [],
            "responses": {
                "200": {"description": "Successful response"},
            },
        }

        # --- 1. HANDLER TYPE INSPECTION ---
        try:
            sig = inspect.signature(handler)
            type_hints = get_type_hints(handler)
        except (ValueError, TypeError):
            # Fallback if the handler is complex
            type_hints = {}
            sig = None
            print(f"WARNING: Could not inspect signature for route {original_path}")

        body_model: Optional[Type[BASE_MODEL]] = None  # type: ignore # Use the BASE_MODEL alias

        # 2. PARAMETER PROCESSING
        if sig:
            for name, param in sig.parameters.items():
                if name == "request":
                    continue

                param_type = type_hints.get(name, str)  # Assume string if no hint

                # A) Path Parameter Detection (Path Parameter)
                path_param_match = re.search(
                    r"\{" + re.escape(name) + r":([a-zA-Z]+)\}", original_path
                )

                if path_param_match:
                    # This is a Path Parameter
                    type_str = path_param_match.group(1)
                    openapi_type = self._get_openapi_type(
                        {"str": str, "int": int, "float": float}.get(
                            type_str.lower(), str
                        )
                    )

                    operation["parameters"].append(
                        {
                            "name": name,
                            "in": "path",
                            "required": True,
                            "schema": {"type": openapi_type},
                            "description": f"Path parameter with type: {type_str}",
                        }
                    )

                # B) Request Body Detection (BASE_MODEL)
                # CRITICAL: Use BASE_MODEL alias for inspection
                elif inspect.isclass(param_type) and issubclass(param_type, BASE_MODEL):
                    if body_model is not None:
                        # Warning: multiple request bodies are not allowed in OpenAPI 3.0
                        print(
                            f"WARNING: Multiple Pydantic models found in the handler of {original_path}. Only the first one will be used."
                        )
                        continue

                    body_model = param_type
                    self._add_pydantic_schema(body_model)

                # C) Query Parameter Detection (Query Parameter)
                elif param.default is not inspect.Parameter.empty or method == "GET":
                    # Consider Query if it has a default value or if it's a GET request

                    # OpenAPI Type
                    schema: Dict[str, Any] = {
                        "type": self._get_openapi_type(param_type)
                    }

                    # If it has a default value
                    if (
                        param.default is not inspect.Parameter.empty
                        and param.default is not None
                    ):
                        schema["default"] = param.default
                        required = False
                    else:
                        required = param.default is inspect.Parameter.empty

                    operation["parameters"].append(
                        {
                            "name": name,
                            "in": "query",
                            "required": required,
                            "schema": schema,
                            "description": f"Query parameter (Query)",
                        }
                    )

        # --- 3. ADD REQUEST BODY ---
        # We only try to add a requestBody if Pydantic is available and a model was found
        if body_model and method in {"POST", "PUT", "PATCH"} and PYDANTIC_AVAILABLE:
            model_name = body_model.__name__

            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{model_name}"}
                    }
                },
            }

        return operation


class OpenAPIPlugin(ViraPlugin):
    """Plugin to add OpenAPI documentation and Swagger UI."""

    def __init__(
        self,
        app: "Virapi",
        title: str = "Virapi API",
        description: str = "",
        version: str = "0.1.0",
    ):
        super().__init__(app)
        self.title = title
        self.description = description
        self.version = version
        self.docs_generator = OpenAPIDocs(
            app, title=title, description=description, version=version
        )
        self.openapi_schema: dict = {}
        self.swagger_html: str = ""

    def register(self):
        """
        Registers the schema generator and documentation routes.
        """
        self.app.add_event_handler("startup", self._generate_static_content)
        self.app.get("/openapi.json", priority=9999)(self.openapi_json_endpoint)
        self.app.get("/docs", priority=9999)(self.swagger_ui_endpoint)

        print(f"INFO: Plugin OpenAPI '{self.title}' registered. Paths added.")

    async def _generate_static_content(self):
        """Startup handler: generates static docs content."""
        self.openapi_schema = self.docs_generator.generate_schema()
        self.swagger_html = self._get_swagger_html()
        print("INFO: OpenAPI static content successfully generated.")

    async def openapi_json_endpoint(self, *_) -> Response:
        """Serves the generated OpenAPI schema."""

        headers = {"Content-Type": "application/json"}
        return Response(
            content=json.dumps(self.openapi_schema).encode("utf-8"),
            status_code=200,
            headers=headers,
        )

    async def swagger_ui_endpoint(self, *_) -> Response:
        """Serves the Swagger user interface."""

        headers = {"Content-Type": "text/html; charset=utf-8"}

        return Response(
            content=self.swagger_html.encode("utf-8"), status_code=200, headers=headers
        )

    def _get_swagger_html(self) -> str:
        """Helper to generate the Swagger UI HTML content."""
        return f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <meta name="description" content="SwaggerUI" />
            <title>{self.title} Docs</title>
            <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
        </head>
        <body>
        <div id="swagger-ui"></div>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js" crossorigin></script>
        <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-standalone-preset.js" crossorigin></script>
        <script>
            window.onload = () => {{
                window.ui = SwaggerUIBundle({{
                    url: '/openapi.json',
                    dom_id: '#swagger-ui',
                    presets: [
                        SwaggerUIBundle.presets.apis,
                        SwaggerUIStandalonePreset
                    ],
                    layout: "StandaloneLayout",
                }});
            }};
        </script>
        </body>
        </html>
        """
