import inspect
import re
import json
from typing import Any, Callable, Dict, Optional, Type, get_type_hints

from pydantic import BaseModel

from vira.plugin import ViraPlugin
from vira.response import Response
from vira.vira import Vira


class OpenAPIDocs:
    """
    Clase para generar el esquema OpenAPI a partir de las rutas de Vira,
    incluyendo soporte para Pydantic.
    """
    def __init__(self, app: "Vira", title: str = "API de Vira", description: str = "", version: str = "0.1.0"):
        self.app = app
        self.title = title
        self.description = description
        self.version = version
        self._schema: Dict[str, Any] = {}
        # Mantiene un registro de los modelos Pydantic ya añadidos para evitar duplicados
        self._registered_schemas: Dict[str, Type[BaseModel]] = {}

    def generate_schema(self) -> Dict[str, Any]:
        """Genera y retorna el esquema OpenAPI completo (JSON/Dict)."""
        
        # Genera el diccionario base del esquema OpenAPI
        self._schema = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description if self.description else f"{self.title} API documentation",
            },
            "paths": self._generate_paths(),
            "components": {
                "schemas": {} 
            },
        }
        
        # Tras generar paths, volcamos los esquemas Pydantic registrados
        for name, model in self._registered_schemas.items():
            self._schema["components"]["schemas"][name] = model.model_json_schema()

        return self._schema

    def _add_pydantic_schema(self, model: Type[BaseModel]):
        """Registra un modelo Pydantic para su inclusión en components/schemas."""
        model_name = model.__name__
        if model_name not in self._registered_schemas:
            self._registered_schemas[model_name] = model
            # En un sistema real, aquí inspeccionaríamos los campos del modelo
            # para registrar modelos anidados si fuera necesario.

    def _get_openapi_type(self, type_hint: Type) -> str:
        """Mapea tipos de Python/Pydantic a tipos básicos de OpenAPI."""
        if type_hint is str:
            return "string"
        if type_hint is int:
            return "integer"
        if type_hint is float:
            return "number"
        if type_hint is bool:
            return "boolean"
        # Manejo simple para otros tipos comunes de Pydantic
        if hasattr(type_hint, '__name__') and type_hint.__name__.lower() == 'decimal':
            return "number"
        return "string" # Default
        

    def _generate_paths(self) -> Dict[str, Any]:
        """
        Itera sobre la lista de rutas en APIRouter y genera el objeto 'paths'.
        """
        paths = {}
        EXCLUDED_PATHS = {"/docs", "/openapi.json"}
        
        routes_list = getattr(self.app.api_router, 'routes', None)

        if not isinstance(routes_list, list):
            print("ADVERTENCIA: No se encontró la lista 'routes' en self.app.api_router. No se generará documentación de rutas.")
            return {}

        for route in routes_list:
            path_pattern = route.path
            handler = route.handler
            
            if path_pattern in EXCLUDED_PATHS:
                continue

            # PASO 1: CONVERTIR EL PATH DE VIRA A PATH DE OPENAPI
            openapi_path = re.sub(r'\{([a-zA-Z0-9_]+):[a-zA-Z]+\}', r'{\1}', path_pattern)

            if openapi_path not in paths:
                paths[openapi_path] = {}

            # route.methods es un Set[str] de los métodos permitidos para esta ruta
            for method in route.methods:
                if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
                    operation = self._generate_operation(method, openapi_path, handler, path_pattern)
                    paths[openapi_path][method.lower()] = operation
        
        return paths

    def _generate_operation(self, method: str, path: str, handler: Callable, original_path: str) -> Dict[str, Any]:
        """Genera el objeto 'operation' (GET, POST, etc.) para una ruta específica, incluyendo Pydantic."""
        
        docstring = handler.__doc__.strip() if handler.__doc__ else ""
        summary = docstring.split('\n')[0]
        description = docstring
        
        operation: Dict[str, Any] = {
            "summary": summary or f"{method} {path}",
            "description": description,
            "tags": ["API"], 
            "parameters": [],
            "responses": {
                "200": {"description": "Respuesta exitosa"},
            },
        }
        
        # --- 1. INSPECCIÓN DE TIPOS DEL HANDLER ---
        try:
            sig = inspect.signature(handler)
            type_hints = get_type_hints(handler)
        except (ValueError, TypeError):
            # Fallback si el handler es algo complejo que inspect no puede manejar
            type_hints = {}
            sig = None
            print(f"ADVERTENCIA: No se pudo inspeccionar la firma para la ruta {original_path}")


        body_model: Optional[Type[BaseModel]] = None
        
        # 2. PROCESAMIENTO DE PARÁMETROS
        if sig:
            for name, param in sig.parameters.items():
                if name == "request": continue 

                param_type = type_hints.get(name, str) # Asumimos string si no hay hint

                # A) Detección de Parámetro de RUTA (Path Parameter)
                # Usamos el regex sobre el path original de Vira
                path_param_match = re.search(r'\{' + re.escape(name) + r':([a-zA-Z]+)\}', original_path)

                if path_param_match:
                    # Este es un parámetro de ruta
                    type_str = path_param_match.group(1)
                    openapi_type = self._get_openapi_type({"str": str, "int": int, "float": float}.get(type_str.lower(), str))
                    
                    operation["parameters"].append({
                        "name": name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": openapi_type}, 
                        "description": f"Parámetro de ruta con tipo: {type_str}"
                    })
                
                # B) Detección de Request Body (Pydantic BaseModel)
                elif inspect.isclass(param_type) and issubclass(param_type, BaseModel):
                    if body_model is not None:
                         # Advertencia: múltiples cuerpos de petición no están permitidos en OpenAPI 3.0
                         print(f"ADVERTENCIA: Múltiples modelos Pydantic encontrados en el handler de {original_path}. Se usará solo el primero.")
                         continue
                         
                    body_model = param_type
                    self._add_pydantic_schema(body_model)
                
                # C) Detección de Parámetro de Consulta (Query Parameter)
                elif param.default is not inspect.Parameter.empty or method == "GET": 
                    # Consideramos Query si tiene un valor por defecto o si es un GET
                    
                    # Tipo OpenAPI
                    schema: Dict[str, Any] = {"type": self._get_openapi_type(param_type)}
                    
                    # Si tiene valor por defecto
                    if param.default is not inspect.Parameter.empty and param.default is not None:
                        schema["default"] = param.default
                        required = False
                    else:
                        required = (param.default is inspect.Parameter.empty)
                        
                    operation["parameters"].append({
                        "name": name,
                        "in": "query",
                        "required": required,
                        "schema": schema, 
                        "description": f"Parámetro de consulta (Query)"
                    })

        # --- 3. AÑADIR REQUEST BODY ---
        if body_model and method in {"POST", "PUT", "PATCH"}:
            model_name = body_model.__name__
            operation["requestBody"] = {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {"$ref": f"#/components/schemas/{model_name}"}
                    }
                }
            }
        
        return operation


class OpenAPIPlugin(ViraPlugin):
    """Plugin para añadir documentación OpenAPI y Swagger UI."""

    def __init__(self, app: 'Vira', title: str = "API de Vira", description: str = "", version: str = "0.1.0"):
        super().__init__(app)
        self.title = title
        self.description = description
        self.version = version
        self.docs_generator = OpenAPIDocs(app, title=title, description=description, version=version)
        self.openapi_schema: dict = {}  
        self.swagger_html: str = ""     
    
    def register(self):
        """
        Registra el generador de esquema y las rutas de documentación.
        """
        self.app.add_event_handler("startup", self._generate_static_content)
        self.app.get("/openapi.json", priority=9999)(self.openapi_json_endpoint)
        self.app.get("/docs", priority=9999)(self.swagger_ui_endpoint)
        
        print(f"INFO: Plugin OpenAPI '{self.title}' registered. Paths added.")

    async def _generate_static_content(self):
        """Handler de startup: genera el contenido estático de docs."""
        self.openapi_schema = self.docs_generator.generate_schema()
        self.swagger_html = self._get_swagger_html()
        print("INFO: Contenido estático de OpenAPI generado correctamente.")

    async def openapi_json_endpoint(self, *_) -> Response:
        """Sirve el esquema OpenAPI generado."""
        
        headers = {
            "Content-Type": "application/json"
        }
        return Response(
            content=json.dumps(self.openapi_schema).encode("utf-8"),
            status_code=200,
            headers=headers
        )

    async def swagger_ui_endpoint(self, *_) -> Response:
        """Sirve la interfaz de usuario de Swagger."""
        
        headers = {
            "Content-Type": "text/html; charset=utf-8"
        }
        
        return Response(
            content=self.swagger_html.encode("utf-8"), 
            status_code=200,
            headers=headers
        )
        
    def _get_swagger_html(self) -> str:
        """Helper para generar el contenido HTML de Swagger UI."""
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
