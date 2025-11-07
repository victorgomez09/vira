from typing import Dict, Any, List, Optional
from http.client import HTTPException
import jwt
from jwt import PyJWTError, ExpiredSignatureError, InvalidSignatureError

from virapi.request.request import Request

class User:
    """Represents an authenticated or anonymous user."""
    def __init__(self, user_id: str = "anonymous", roles: Optional[List[str]] = None, email: Optional[str] = None):
        self.user_id = user_id
        self.roles = roles if roles is not None else []
        self.email = email

    @property
    def is_anonymous(self) -> bool:
        """Verify if the user is anonymous."""
        return self.user_id == "anonymous"
    
    def __repr__(self) -> str:
        return f"<AuthUser id={self.user_id} email={self.email} roles={self.roles}>"

# --- Global Configuration ---
JWT_SECRET_KEY: str = ""
JWT_ALGORITHMS: List[str] = ["HS256"]

def set_jwt_config(secret_key: str, algorithms: Optional[List[str]] = None):
    """Sets the global configuration for JWT validation."""
    global JWT_SECRET_KEY
    global JWT_ALGORITHMS
    JWT_SECRET_KEY = secret_key
    if algorithms:
        JWT_ALGORITHMS = algorithms

def validate_jwt_token(token: Optional[str]) -> Dict[str, Any]:
    """
    Performs cryptographic and claims validation using PyJWT.
    """
    result: Dict[str, Any] = {
        "is_valid": False,
        "user_id": "anonymous",
        "roles": []
    }
    
    if not token or not JWT_SECRET_KEY:
        return result

    try:
        payload = jwt.decode(
            jwt=token, 
            key=JWT_SECRET_KEY, 
            algorithms=JWT_ALGORITHMS,
            # TODO: Add more options as needed like 'audience', 'issuer', etc.
        )
        
        result["is_valid"] = True
        result["user_id"] = payload.get("sub", "unknown") 
        result["roles"] = payload.get("roles", [])
        
    except ExpiredSignatureError:
        print("DEBUG: JWT Validation Failed: Token has expired.")
    except (PyJWTError, InvalidSignatureError) as e:
        print(f"DEBUG: JWT Validation Failed: {e.__class__.__name__} - {e}")
        
    return result

# --- User Injection Functions ---

def get_current_user_and_attach(request: Request) -> User:
    """
    Extracts the token, validates it, and attaches the User object to request.user.
    Does NOT raise exceptions; always returns a User (authenticated or anonymous).
    """
    # 1. Quick check if user is already attached (avoids double-check)
    user = getattr(request, 'user', None)
    if user is not None:
        return user

    # 2. Extract token
    auth_header = request.headers.get("Authorization")
    token = auth_header.split("Bearer ")[1] if auth_header and auth_header.startswith("Bearer ") else None

    # 3. Validate token
    validation_result = validate_jwt_token(token)

    # 4. Build User
    user = User(
        user_id=validation_result["user_id"],
        roles=validation_result["roles"]
    ) if validation_result["is_valid"] else User()

    # CRUCIAL: Attach the User object to the Request (assumes virapi Request accepts attributes)
    setattr(request, 'user', user)
    return user


def requires_authentication(request: Request) -> User:
    """Raises 401 if user is anonymous."""
    user = get_current_user_and_attach(request)

    if user.is_anonymous:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    return user


def requires_role(request: Request, role: str) -> User:
    """Raises 401 if not authenticated, or 403 if does not have the role."""
    # 401 is handled internally by requires_authentication
    user = requires_authentication(request)

    # 2. Authorization Check (403)
    if role not in user.roles:
        raise HTTPException(
            status_code=403,
            detail=f"Access denied. Requires role: '{role}'",
        )
    
    return user