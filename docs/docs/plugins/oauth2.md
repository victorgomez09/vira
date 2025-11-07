# virapi OAuth2 Plugin (OAuth 2.0 Client & Flows)

The `ViraOAuth2Plugin` provides built-in support for common OAuth 2.0 authentication flows, primarily focusing on the **Authorization Code Flow with PKCE** for user web sessions and the **Client Credentials Flow** for machine-to-machine security.

## 1. Installation and Configuration

The plugin must be configured with details for your external Identity Provider (IdP) like Google, Auth0, etc.

| Config Key | Type | Description |
| :--- | :--- | :--- |
| **`client_id`** | `str` | Your application's client ID. |
| **`client_secret`** | `str` | Your application's client secret. |
| **`auth_url`** | `str` | The IdP's Authorization endpoint URL. |
| **`token_url`** | `str` | The IdP's Token exchange endpoint URL. |
| **`userinfo_url`** | `str` | The URL to retrieve user profile data (e.g., email) after token exchange. |
| **`redirect_uri`** | `str` | Your application's publicly accessible callback URL (e.g., `https://api.app.com/oauth/callback`). |
| **`scopes`** | `str` | Space-separated list of scopes to request (e.g., `"openid profile email"`). |

### Example Registration

```python
# app.py

from virapi import virapi
from plugins.oauth2.oauth2 import ViraOAuth2Plugin

app = virapi()

app.add_plugin(
    ViraOAuth2Plugin,
    config={
        "client_id": "YOUR_CLIENT_ID",
        "client_secret": "YOUR_CLIENT_SECRET",
        "auth_url": "[https://auth.provider.com/authorize](https://auth.provider.com/authorize)",
        "token_url": "[https://auth.provider.com/token](https://auth.provider.com/token)",
        "userinfo_url": "[https://auth.provider.com/userinfo](https://auth.provider.com/userinfo)",
        "redirect_uri": "http://localhost:8000/oauth/callback",
        "scopes": "openid profile email"
    }
)
```


## 2. Authorization Code Flow (User Web Sessions)
This flow is handled automatically by the plugin. It uses an internal dictionary to manage sessions (for educational purposes/simple deployments) and a cookie to track the user.The plugin registers the following routes for you:

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| /oauth/login | GET | Generates PKCE parameters and redirects the user to the auth_url. |
| /oauth/callback | GET | Receives the authorization code, exchanges it for tokens, fetches user info, and creates a local session/cookie. |

### Route Protection: ```@oauth_session_required```
Use this decorator to protect user-facing routes. If no valid session is found, it automatically issues a 302 Found redirect to the /oauth/login endpoint.

```python
import oauth_session_required
from plugins.jwt.base import User

@app.get("/dashboard")
@oauth_session_required
async def user_dashboard(request: Request):
    # If unauthenticated, user is redirected to /oauth/login
    user: User = request.user 
    return html_response(f"<h1>Dashboard for {user.email}</h1>")
```

## 3. Client Credentials Flow (Machine-to-Machine)
This flow allows services to authenticate and receive an access token directly using their client_id and client_secret.

### Token Endpoint: ```@client_credentials_token_endpoint```
The plugin registers a token endpoint at /oauth/client-token and this decorator handles the authentication logic, token request to the IdP, and response formatting.

```python
from plugins.oauth2.oauth2 import client_credentials_token_endpoint

# The handler must be defined, but the decorator handles the response
@app.post("/oauth/client-token")
@client_credentials_token_endpoint 
async def client_token(request: Request):
    pass 
```

**Usage**: A client service POSTs *client_id* and *client_secret* to this endpoint to receive the access token.
