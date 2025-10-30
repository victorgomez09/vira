from typing import Tuple, Callable, List
from vira.types import HandlerType, Methods, QueryExtractor, BodyExtractor

RouteInfo = Tuple[str, HandlerType, Methods, QueryExtractor, BodyExtractor]
DecoratorReturn = Callable[[HandlerType], HandlerType]

class ApiRouter:
    """
    e.g:
    router1_pkg_sample_1 = ApiRouter()

    @router1_pkg_sample_1.get("/home")
    async def home(request_data):
        print("home triggered")
    
    router2_pkg_sample_2 = ApiRouter()
    @router2_pkg_sample_2.get("/about")
    async def about(request_data):
        print("about triggered")

    app = Vira()
    app.include_routes([router1_pkg_sample_1, router2_pkg_sample_2])
    """
    __slots__ = ["routes"]

    def __init__(self):
        self.routes: List[RouteInfo] = []

    def decorator(self, path: str, method: Methods, query_string_extractor: QueryExtractor = None, body_extractor: BodyExtractor = None) -> DecoratorReturn:
        def wrap(handler: HandlerType) -> HandlerType:
            self.routes.append((path, method, query_string_extractor, body_extractor))

            return handler
        
        return wrap
    
    def get(self, path: str, query_string_extractor: QueryExtractor = None, body_extractor: BodyExtractor = None) -> DecoratorReturn:
        return self.decorator(path, Methods.GET, query_string_extractor, body_extractor)
    
    def multi_methods(self, path: str, methods: List[Methods], query_string_extractor: QueryExtractor = None, body_extractor: BodyExtractor = None) -> DecoratorReturn:
        def decorator(handler: HandlerType) -> HandlerType:
            for method in methods:
                self.routes.append((path, method, query_string_extractor, body_extractor))
            
            return handler

        return decorator
    
