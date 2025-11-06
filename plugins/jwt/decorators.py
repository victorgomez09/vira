from functools import wraps
from http.client import HTTPException
from typing import Awaitable, Callable, Any

from plugins.jwt.base import requires_authentication, requires_role
from vira.response import Response

RouteHandler = Callable[[Any], Awaitable[Response]]

def jwt_authenticated_only(func: RouteHandler) -> RouteHandler:
    """
    Decorator that ensures the Request is authenticated with a valid JWT (401).
    """
    @wraps(func)
    async def wrapper(request: Any, *args, **kwargs) -> Response:
        try:
            # Calls the security logic that raises HTTPException(401)
            requires_authentication(request) 
        except HTTPException as e:
            # Captures the error and returns the HTTP response
            return Response(
                e.detail, 
                status_code=e.status_code, 
                headers=e.headers
            )
            
        return await func(request, *args, **kwargs)
        
    return wrapper


def jwt_requires_role(role: str) -> Callable[[RouteHandler], RouteHandler]:
    """
    Decorator that ensures the authenticated user has a specific role (403).
    """
    def decorator(func: RouteHandler) -> RouteHandler:
        @wraps(func)
        async def wrapper(request: Any, *args, **kwargs) -> Response:
            try:
                # Calls the security logic that raises HTTPException(401 or 403)
                requires_role(request, role) 
            except HTTPException as e:
                # Captures the error and returns the HTTP response
                return Response(
                    e.detail, 
                    status_code=e.status_code, 
                    headers=e.headers
                )
            
            return await func(request, *args, **kwargs)
        return wrapper
    return decorator