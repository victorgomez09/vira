# vira_openapi/plugin.py (Requiere el código del generador de la sección anterior: OpenAPIDocs)
import inspect
from typing import TYPE_CHECKING, Any, Callable, Dict
from urllib.parse import unquote

# Asumiremos que ViraPlugin y OpenAPIDocs son accesibles.
from vira.plugin import ViraPlugin
from vira.response import json_response, Response # Necesitas estas respuestas
class OpenAPIDocs:
    """
    Clase para generar el esquema OpenAPI a partir de las rutas de Vira.
    """
    def __init__(self, app: 'Vira', title: str = "API de Vira", version: str = "0.1.0"):
        self.app = app
        self.title = title
        self.version = version
        self._schema: Dict[str, Any] = {}

    def generate_schema(self) -> Dict[str, Any]:
        """Genera y retorna el esquema OpenAPI completo (JSON/Dict)."""
        
        # Genera el diccionario base del esquema OpenAPI
        self._schema = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.app.__doc__.strip() if self.app.__doc__ else "Una aplicación ASGI simple.",
            },
            "paths": self._generate_paths(),
            "components": {
                # Aquí se añadirían los modelos Pydantic si se usaran
                "schemas": {} 
            },
        }
        return self._schema

    def _generate_paths(self) -> Dict[str, Any]:
        """
        Itera sobre el APIRouter y genera el objeto 'paths'.
        NOTA: Necesitas adaptar esta parte a la estructura interna real de tu APIRouter.
        Asumimos que APIRouter.routes_data es el mapa de rutas.
        """
        paths = {}
        
        # Iterar sobre las rutas registradas en el APIRouter principal de la aplicación.
        # **ESTE CÓDIGO DEPENDE DE CÓMO ALMACENA INTERNAMENTE LAS RUTAS TU `APIRouter`**
        # Si tienes la lista de rutas en `self.app.api_router.routes_data`:
        if hasattr(self.app.api_router, 'routes_data'):
            for path_pattern, route_mapping in self.app.api_router.routes_data.items():
                path_item = {}
                
                # Descodifica la URL si usa codificación (aunque en Vira no suele ser necesario)
                openapi_path = unquote(path_pattern) 
                
                for method, handler in route_mapping.items():
                    # Solo incluimos métodos HTTP comunes
                    if method in {"GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"}:
                        operation = self._generate_operation(method, openapi_path, handler)
                        path_item[method.lower()] = operation
                
                if path_item:
                    paths[openapi_path] = path_item
        
        return paths

    def _generate_operation(self, method: str, path: str, handler: Callable) -> Dict[str, Any]:
        """Genera el objeto 'operation' (GET, POST, etc.) para una ruta específica."""
        
        # Usa la docstring como descripción (solo la primera línea como resumen)
        docstring = handler.__doc__.strip() if handler.__doc__ else ""
        summary = docstring.split('\n')[0]
        description = docstring
        
        operation: Dict[str, Any] = {
            "summary": summary or f"{method} {path}",
            "description": description,
            "tags": ["default"], # Se podrían añadir etiquetas personalizadas
            "parameters": [],
            "responses": {
                "200": {"description": "Respuesta exitosa"},
                "404": {"description": "No encontrado"},
            },
        }

        # Inspeccionar la firma del manejador para ver parámetros de ruta
        try:
            sig = inspect.signature(handler)
            for name, param in sig.parameters.items():
                if name != "request": # Excluye el objeto Request
                    # En Vira, los parámetros de ruta se inyectan por nombre
                    # Aquí solo podemos asumir el tipo básico si no usamos Pydantic
                    
                    # Simulación de extracción de parámetros de ruta
                    # TODO: Mejorar la inferencia de tipos y si es 'path' o 'query'
                    
                    # Un enfoque simple: si el parámetro está en la ruta, es un path parameter
                    if f"{{{name}}}" in path or f"{{{name}:" in path:
                         operation["parameters"].append({
                            "name": name,
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"}, # Se podría mejorar la inferencia
                        })

        except ValueError:
            # Puede fallar si el handler no es una función simple
            pass

        return operation


class OpenAPIPlugin(ViraPlugin):
    """Plugin para añadir documentación OpenAPI y Swagger UI."""

    def __init__(self, app: 'Vira', title: str = "API de Vira", version: str = "0.1.0"):
        super().__init__(app)
        self.title = title
        self.version = version
        self.docs_generator = OpenAPIDocs(app, title=title, version=version)
    
    def register(self):
        """
        Registra el generador de esquema y las rutas de documentación
        en el evento de inicio de Vira.
        """
        # Añadir el handler de inicio al Vira principal
        self.app.add_event_handler("startup", self._generate_and_register_routes)
        print(f"INFO: Plugin OpenAPI '{self.title}' registrado. Se iniciará en 'startup'.")

    async def _generate_and_register_routes(self):
        """Genera el esquema OpenAPI y registra las rutas /openapi.json y /docs."""
        
        # 1. Generar el esquema UNA VEZ
        openapi_schema = self.docs_generator.generate_schema()
        
        # 2. Generar el contenido HTML UNA VEZ
        swagger_html = self._get_swagger_html()

        # 3. Registrar la ruta del JSON de OpenAPI
        # Usamos app.get() para registrar una función lambda que ignora el 'request'
        # y devuelve el esquema JSON generado.
        self.app.get("/openapi.json", priority=9999)(
            lambda request: json_response(openapi_schema)
        )

        # 4. Registrar la ruta de Swagger UI
        # Usamos app.get() para registrar una función lambda que ignora el 'request'
        # y devuelve el HTML generado.
        self.app.get("/docs", priority=9999)(
            lambda request: Response(
                content=swagger_html.encode("utf-8"),
                media_type="text/html",
                status_code=200
            )
        )
        
        print("INFO: Rutas de documentación OpenAPI registradas en /openapi.json y /docs")

    def _get_swagger_html(self) -> str:
        """Helper para generar el contenido HTML de Swagger UI."""
        # Mueve aquí el código HTML de Swagger UI para mayor limpieza.
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title} Docs</title>
            <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
            <script>
            SwaggerUIBundle({{
                url: "/openapi.json",
                dom_id: '#swagger-ui',
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIBundle.SwaggerUIStandalonePreset
                ],
                layout: "BaseLayout",
            }})
            </script>
        </body>
        </html>
        """