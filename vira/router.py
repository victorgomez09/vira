from dataclasses import dataclass
from typing import Dict, List, Optional

from vira.exceptions import MethodNotAllowedException
from vira.types import BodyExtractor, HandlerType, Methods, QueryExtractor


@dataclass
class _Route:
    handler: HandlerType
    query_string_extractor: QueryExtractor
    body_extractor: BodyExtractor

# This will make the magic of association between path simillarities
class _NodeRoute:
    """
    Visual example
    routes
        -> / -> home handler
        -> /users -> users handler
        -> files/documents -> documents handler

    root [segment = /, children = Users, Files, handler = home/index handler]
        -> users [segment = users, children = ..., handler = users handler]
        -> files [segment = files, children = documents, handler = None]
            -> documents [segment = documents, children = ..., handler = documents handler]
    ...
    and that continue as required, allowing to add more items and nesting as required
    """
    __slots__ = ["segment", "children", "handler"]

    def __init__(self, segment: str = ""):
        self.segment: str = segment # the par of the route
        self.children: Dict[str, _NodeRoute] = {} # dict segment and its node route
        self.routes: Dict[Methods, Optional[_Route]] = {enum_value: None for enum_value in Methods}
    
    def __repr__(self) -> str:
        return f"NodeRoute({self.segment}) children = {len(self.children)}"
    
# This will be the interface with our users
class Router:
    __slots__ = ["root"]

    def __init__(self):
        self.root = _NodeRoute()

    @staticmethod
    def get_segments(path: str) -> List[str]:
        if path == "" or path == "/":
            return ["/"]
        
        return ["/"] + [seg for seg in path.split("/") if seg]

    def add_route(self, path: str, handler: HandlerType, method: Methods = Methods.GET, query_string_extractor: QueryExtractor = None, body_extractor: BodyExtractor = None) -> None:
        assert method in Methods, f"Method {method} not supported"
        
        current = self.root
        segments = self.get_segments(path)
        # insertion DFS like
        for segment in segments:
            if segment not in current.children:
                current.children[segment] = _NodeRoute(segment)
            
            # swp to the next nest level
            current = current.children[segment]

        current.routes[method] = _Route(handler, query_string_extractor, body_extractor)
    
    def get_route(self, path: str, method: Methods) -> Optional[_Route]:
        assert method in Methods, f"Method {method} not supported"
        
        current = self.root
        segments = self.get_segments(path)
        for segment in segments:
            if segment not in current.children:
                return None
            
            current = current.children[segment]

        # method not allowed
        if current.routes[Methods(method)] is None: # when detected method is not allowed it raises an exception
            raise MethodNotAllowedException(f"Method {method} not allowed on path {path}")
        
        return current.routes[Methods(method)]