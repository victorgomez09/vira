from vira.plugin import ViraPlugin 
from vira.response import Response, redirect_response, text_response # Asume importación del core
from http.client import HTTPException
from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, Awaitable, Dict, List, Optional
import json

from .client_security import (
    configure_oauth_client, 
    get_authorization_url_pkce, 
    handle_callback_and_create_session, 
    requires_oauth_session, 
    client_credentials_auth_real,
    User 
)

if TYPE_CHECKING:
    from vira import Vira
    
RouteHandler = Callable[[Any], Awaitable[Response]]

# --- Decorators to protect routes ---

def oauth_session_required(func: RouteHandler) -> RouteHandler:
    """
    [Authorization Code / PKCE Flow]
    Ensures web user authentication (via cookie/session). Redirects to login if anonymous.
    """
    @wraps(func)
    async def wrapper(request: Any, *args, **kwargs) -> Response:
        try:
            requires_oauth_session(request) 
        except HTTPException as e:
            # If it's 401 and has the redirect hint, we redirect.
            if e.status_code == 401 and e.headers.get("Location"):
                 return redirect_response(e.headers["Location"])
                 
            return Response(
                e.detail, 
                status_code=e.status_code, 
                headers=e.headers
            )
            
        return await func(request, *args, **kwargs)
        
    return wrapper

def client_credentials_token_endpoint(func: RouteHandler) -> RouteHandler:
    """
    [Client Credentials Flow]
    Decorator to create an endpoint that generates the Client Credentials token.
    Calls the actual token retrieval logic and returns the JSON response.
    """
    @wraps(func)
    async def wrapper(request: Any, *args, **kwargs) -> Response:
        try:
            # Obtain the real token from the OAuth server using Client ID/Secret
            token_response_data = client_credentials_auth_real()
            
            return Response(
                json.dumps(token_response_data),
                status_code=200,
                headers={"Content-Type": "application/json"}
            )
        except HTTPException as e:
            return Response(
                e.detail, 
                status_code=e.status_code,
            )
        except Exception as e:
            return text_response(f"Error obtaining service token: {e}", status_code=500)
            
    return wrapper


class ViraOAuth2Plugin(ViraPlugin):
    """
    Plugin for Vira that implements OAuth 2.0 flows (Authorization Code/PKCE, Client Credentials).
    """
    def __init__(self, app: 'Vira', **kwargs):
        super().__init__(app, **kwargs)
        self.config = kwargs
        
    def _add_auth_routes(self):
        """Adds the login, callback, and Client Credentials endpoint routes to the router."""
        router = self.app.api_router

        # 1. Routes for Authorization Code + PKCE
        @router.get("/oauth/login")
        async def oauth_login(request: Any):
            """Starts the PKCE flow, redirects to the IdP."""
            auth_url = get_authorization_url_pkce()
            return redirect_response(auth_url)

        @router.get("/oauth/callback")
        async def oauth_callback(request: Any):
            """Handles the authorization code, obtains tokens and user info."""
            return await handle_callback_and_create_session(request)

        # 2. Endpoint for Client Credentials (POST)
        @router.post("/oauth/client-token")
        @client_credentials_token_endpoint
        async def client_token(request: Any):
            """Endpoint that returns a Client Credentials token."""
            # The client_credentials_token_endpoint decorator already handles the response
            pass


    def register(self):
        """
        Initializes the configuration and registers the necessary routes.
        """
        required_keys = ["client_id", "client_secret", "auth_url", "token_url", "userinfo_url", "redirect_uri"]
        if not all(k in self.config for k in required_keys):
            raise ValueError(f"ViraOAuth2Plugin requires the following configurations: {required_keys}")

        configure_oauth_client(self.config)
        self._add_auth_routes()


# --- Key Exports for the User ---
__all__ = [
    "ViraOAuth2Plugin", 
    "User", 
    "oauth_session_required",
    "client_credentials_token_endpoint",
]