# virapi JWT AuthPlugin (JSON Web Token Authentication)

The `ViraJWTAuthPlugin` provides a robust, token-based authentication and role-based authorization mechanism using **JSON Web Tokens (JWT)**. It relies on the presence of a `Authorization: Bearer <token>` header in incoming requests.

## 1. Installation and Configuration

The plugin must be registered during application startup by providing the essential security parameters.

| Parameter | Type | Description |
| :--- | :--- | :--- |
| **`secret_key`** | `str` | **Required.** The cryptographic key used to sign and verify JWTs. Must be a secure, long, randomly generated string. |
| **`algorithms`** | `List[str]` | Optional list of allowed JWT algorithms (e.g., `["HS256"]`). Defaults to `["HS256"]`. |

### Example Registration

```python
# app.py

from virapi import virapi
from plugins.jwt.jwt import ViraJWTAuthPlugin

app = virapi()

# Register the plugin with your security configuration
app.add_plugin(
    ViraJWTAuthPlugin,
    secret_key="your-highly-secure-32-byte-secret-key",
    algorithms=["HS256"],
)
```

## 2. Route Protection (Decorators)
The plugin provides decorators to enforce security policies on your route handlers. If a requirement is not met, the decorator intercepts the request and returns the appropriate HTTP error response (401 or 403).

```@jwt_authenticated_only```
Ensures the request contains a valid and unexpired JWT.

| Failure Condition | HTTP Status | Headers |
| :--- | :--- | :--- |
| Missing or invalid token | 401 Unauthorized | WWW-Authenticate: Bearer |


```python
from plugins.jwt.decorators import jwt_authenticated_only
from plugins.jwt.base import User, create_jwt_token # Helper functions

router = APIRouter()

@router.get("/profile")
@jwt_authenticated_only
async def get_user_profile(request: Request):
    # If the decorator passed, a User object is available on the request
    user: User = request.user 
    return json_response({"user_id": user.user_id, "roles": user.roles})
```

```@jwt_requires_role(role)```
Ensures the user has a valid JWT and that the token's payload contains the specified role in its list of roles.

| Failure Condition | HTTP Status |
| :--- | :--- |
| Missing/Invalid token | 401 Unauthorized |
| Token valid, but role missing | 403 Forbidden |


```python
@router.post("/admin/settings")
@jwt_requires_role("admin")
async def update_settings(request: Request):
    # This handler only runs if the token is valid and contains "admin" role
    return text_response("Settings updated by admin.")
```