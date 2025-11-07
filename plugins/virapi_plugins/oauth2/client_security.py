import base64
import hashlib
import os
import urllib.parse
from http.client import HTTPException
from typing import Any, Dict
import requests

from plugins.jwt.base import User
from virapi.response import Response, redirect_response, text_response 

# --- Global Configuration ---
CLIENT_ID: str = ""
CLIENT_SECRET: str = ""
AUTH_URL: str = ""
TOKEN_URL: str = ""
USERINFO_URL: str = ""
REDIRECT_URI: str = ""
SCOPES: str = "profile email"

# Session storage: In production, this MUST be an external database (e.g. Redis).
ACTIVE_SESSIONS: Dict[str, Any] = {} 

# --- PKCE Utility Functions ---

def _generate_code_verifier() -> str:
    """Generates a secure code verifier (RFC 7636)."""
    return base64.urlsafe_b64encode(os.urandom(32)).rstrip(b'=').decode('ascii')

def _generate_code_challenge(verifier: str) -> str:
    """Generates the code challenge (S256)."""
    sha256 = hashlib.sha256(verifier.encode('ascii')).digest()
    return base64.urlsafe_b64encode(sha256).rstrip(b'=').decode('ascii')


def configure_oauth_client(config: Dict[str, Any]):
    """Sets the global configuration parameters for the OAuth 2.0 client."""
    global CLIENT_ID, CLIENT_SECRET, AUTH_URL, TOKEN_URL, USERINFO_URL, REDIRECT_URI, SCOPES
    CLIENT_ID = config["client_id"]
    CLIENT_SECRET = config["client_secret"]
    AUTH_URL = config["auth_url"]
    TOKEN_URL = config["token_url"]
    USERINFO_URL = config["userinfo_url"]
    REDIRECT_URI = config["redirect_uri"]
    SCOPES = config.get("scopes", SCOPES)

# --- Authorization Code & PKCE Flow (For Web Users) ---

def get_authorization_url_pkce() -> str:
    """Generates the URL to start the authentication flow with PKCE."""
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)
    session_id = base64.urlsafe_b64encode(os.urandom(16)).rstrip(b'=').decode('ascii')

    # Store the verifier for the callback (used as 'state')
    ACTIVE_SESSIONS[session_id] = {'code_verifier': code_verifier}
    
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": session_id,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"

async def handle_callback_and_create_session(request: Any) -> Response:
    """
    Handles the callback, performs the code/PKCE exchange, and creates the local session.
    """
    # Assumes request.query_params is available
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    if not code or not state:
        return text_response("Error 400: Authorization code or state is missing.", status_code=400)

    # 1. Validate 'state' and retrieve the code_verifier
    session_data = ACTIVE_SESSIONS.pop(state, None)
    if not session_data or 'code_verifier' not in session_data:
        return text_response("Error 400: Invalid or expired authentication state.", status_code=400)

    code_verifier = session_data['code_verifier']

    # 2. Exchange Code for Token (Actual HTTP POST call)
    token_data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
        # Note: client_secret is NOT included for PKCE. If the IdP requires it,
        # it would be added here.
    }
    
    try:
        # Synchronous request, consider using 'httpx' if virapi needs to be 100% asynchronous.
        token_response = requests.post(TOKEN_URL, data=token_data)
        token_response.raise_for_status() 
        token_json = token_response.json()
        access_token = token_json.get("access_token")

    except requests.exceptions.RequestException as e:
        return text_response(f"Error 500: Failed to exchange token. Detail: {e}", status_code=500)

    # 3. Obtain User Information (Actual HTTP GET call)
    try:
        user_info_headers = {"Authorization": f"Bearer {access_token}"}
        user_info_response = requests.get(USERINFO_URL, headers=user_info_headers)
        user_info_response.raise_for_status()
        user_info = user_info_response.json()
    except requests.exceptions.RequestException as e:
        return text_response(f"Error 500: Failed to obtain user information. Detail: {e}", status_code=500)

    # 4. Create virapi local session
    user_id = user_info.get("sub") or user_info.get("email") or "unknown_oauth_user"
    email = user_info.get("email")
    
    new_user = User(user_id=user_id, roles=["oauth_user"], email=email)
    
    session_token = base64.urlsafe_b64encode(os.urandom(24)).rstrip(b'=').decode('ascii')
    ACTIVE_SESSIONS[session_token] = new_user

    # 5. Redirect with session cookie
    response = redirect_response("/")
    response.headers["Set-Cookie"] = f"session_id={session_token}; HttpOnly; Path=/; Secure; SameSite=Lax"
    
    return response

# --- Client Credentials Flow (For machine-to-machine services) ---

def client_credentials_auth_real() -> Dict[str, Any]:
    """
    Makes the actual HTTP POST call to obtain a Client Credentials token.
    Returns the JSON response from the token (including access_token).
    """
    token_data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": SCOPES 
    }
    
    try:
        token_response = requests.post(TOKEN_URL, data=token_data)
        token_response.raise_for_status()
        return token_response.json()
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to obtain Client Credentials token: {e}")


# --- Session Check Functions ---

def get_current_oauth_user(request: Any) -> User:
    """Retrieve the User object from the active session (cookie) and attach it to the request."""
    # Assume that request.cookies is a dict (attached by virapi)
    session_token = getattr(request, 'cookies', {}).get("session_id")
    
    user_object = ACTIVE_SESSIONS.get(session_token)
    user = user_object if isinstance(user_object, User) else None
    
    if user:
        setattr(request, 'user', user) 
        return user
    
    anonymous_user = User()
    setattr(request, 'user', anonymous_user)
    return anonymous_user

def requires_oauth_session(request: Any) -> User:
    """Check if a valid session exists (for Auth Code Flow). Raises 401 if it fails."""
    user = get_current_oauth_user(request)
    
    if user.is_anonymous:
        # The outer decorator will use "Location" to redirect
        raise HTTPException(
            status_code=401,
            detail="Session required.",
            headers={"Location": "/oauth/login"}
        )
        
    return user