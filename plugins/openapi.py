import re
import json
from typing import Any, Callable, Dict

from vira.plugin import ViraPlugin
from vira.response import Response
from vira.vira import Vira


class OpenAPIDocs:
    """
    Class to generate OpenAPI schema from Vira routes
    """
    def __init__(self, app: "Vira", title: str = "Vira API", description: str = "", version: str = "0.1.0"):
        self.app = app
        self.title = title
        self.description = description
        self.version = version
        self._schema: Dict[str, Any] = {}

    def generate_schema(self) -> Dict[str, Any]:
        """Generates and return OpenAPI full scheme (JSON/Dict)."""
        
        self._schema = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description or f"{self.title} API documentation.",
            },
            "paths": self._generate_paths(),
            "components": {
                # TODO: Implement model extraction from Pydantic
                "schemas": {} 
            },
        }
        return self._schema

    def _generate_paths(self) -> Dict[str, Any]:
        """
        Iterate over the list of routes in APIRouter and generate the 'paths' object
        in the dictionary format required by OpenAPI.
        """
        paths = {}
        EXCLUDED_PATHS = {"/docs", "/openapi.json"}
        
        routes_list = getattr(self.app.api_router, 'routes', None)

        if not isinstance(routes_list, list):
            print("WARNING: 'routes' list not found in self.app.api_router or it is not a list. Route documentation will not be generated.")
            return {}

        for route in routes_list:
            path_pattern = route.path
            handler = route.handler
            
            if path_pattern in EXCLUDED_PATHS:
                continue

            openapi_path = re.sub(r'\{([a-zA-Z0-9_]+):[a-zA-Z]+\}', r'{\1}', path_pattern)

            if openapi_path not in paths:
                paths[openapi_path] = {}

            for method in route.methods:
                if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
                    operation = self._generate_operation(method, openapi_path, handler, path_pattern)
                    paths[openapi_path][method.lower()] = operation
        
        return paths

    def _generate_operation(self, method: str, path: str, handler: Callable, original_path: str) -> Dict[str, Any]:
        """Generate the 'operation' object (GET, POST, etc.) for a specific path."""
        
        docstring = handler.__doc__.strip() if handler.__doc__ else ""
        summary = docstring.split('\n')[0]
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

        param_regex = re.compile(r'\{([a-zA-Z0-9_]+):([a-zA-Z]+)\}')
        matches = param_regex.findall(original_path)
        
        TYPE_MAP = {
            "str": "string",
            "int": "integer",
            "float": "number",
        }

        for name, type_str in matches:
            openapi_type = TYPE_MAP.get(type_str.lower(), "string")

            operation["parameters"].append({
                "name": name,
                "in": "path",
                "required": True,
                "schema": {"type": openapi_type},
                "description": f"Path parameter of type: {type_str}"
            })
            
        # ----------------------------------------------------------------
        # TODO: Logic to infer QUERY parameters and Request Body (Pydantic models)
        # ----------------------------------------------------------------
        
        return operation


class OpenAPIPlugin(ViraPlugin):
    """Plugin to add OpenAPI and Swagger UI documentation."""

    def __init__(self, app: 'Vira', title: str = "Vira API", description: str = "", version: str = "0.1.0"):
        super().__init__(app)
        self.title = title
        self.description = description
        self.version = version
        self.docs_generator = OpenAPIDocs(app, title=title, description=description, version=version)
        self.openapi_schema: dict = {}
        self.swagger_html: str = ""
    
    def register(self):
        """
        Register the schema generator and documentation routes.
        """
        self.app.add_event_handler("startup", self._generate_static_content)
        
        self.app.get("/openapi.json", priority=9999)(self.openapi_json_endpoint)
        self.app.get("/docs", priority=9999)(self.swagger_ui_endpoint)
        
        print(f"INFO: Plugin OpenAPI '{self.title}' registered. Paths added.")

    async def _generate_static_content(self):
        """Startup handler: generates the static content for docs."""
        self.openapi_schema = self.docs_generator.generate_schema()
        self.swagger_html = self._get_swagger_html()
        print("INFO: Static content for OpenAPI generated successfully.")

    async def openapi_json_endpoint(self, *_) -> Response:
        """Serves the generated OpenAPI schema."""

        headers = {
            "Content-Type": "application/json"
        }
        return Response(
            content=json.dumps(self.openapi_schema).encode("utf-8"),
            status_code=200,
            headers=headers
        )

    async def swagger_ui_endpoint(self, *_) -> Response:
        """Serves the Swagger UI."""
        
        headers = {
            "Content-Type": "text/html; charset=utf-8"
        }
        
        return Response(
            content=self.swagger_html.encode("utf-8"), 
            status_code=200,
            headers=headers
        )
        
    def _get_swagger_html(self) -> str:
        """Helper to generate the HTML content for Swagger UI."""

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
