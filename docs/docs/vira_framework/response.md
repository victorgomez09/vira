# Response Object

## Overview

The `Response` class is used to construct the HTTP response sent back to the client. It handles content serialization, header management (including cookies), and conversion into the standard ASGI response format.

## Key Components

| Component | Description |
| :--- | :--- |
| **`Response`** (Class) | The object representing the outgoing HTTP response. |
| **`status_code`** | The HTTP status code (integer). |
| **`headers`** | A dictionary of response headers. |
| **`body`** | The response content as bytes. |
| **`_process_content`** | Internal method that converts content (str, dict, list) to bytes and performs **automatic Content-Type detection**. |
| **`to_asgi_response()`** | Converts the internal state into the ASGI-compliant dictionary format. |
| **`set_cookie()`** | Adds a `Set-Cookie` header with various options (expires, path, domain, secure, httponly, samesite). |
| **Utility Functions** | `json_response()`, `html_response()`, `text_response()`, `redirect_response()`. |

## How to Use

### 1. Basic Response Construction

```python
from virapi.response import Response, json_response, HTTPStatus

# Standard way
response = Response(
    content="Hello, world!",
    status_code=HTTPStatus.HTTP_200_OK,
    headers={"X-Custom": "Value"}
)

# Using a helper for JSON (recommended)
response = json_response(
    content={"message": "Created"},
    status_code=201
)


### 2. Automatic Content-Type Detection
The framework automatically infers the Content-Type if not explicitly provided:

dict or list content -> application/json

str content containing <html or <!DOCTYPE -> text/html

All other str content -> text/plain

### 3. Setting Cookies
Use the set_cookie method on a Response instance.

```python
from virapi.response import text_response
from datetime import datetime, timedelta

response = text_response("Cookie set!")
```

# Set a session cookie
response.set_cookie("session_id", "abc12345", httponly=True)

# Set a persistent cookie that expires in 7 days
expires_date = datetime.now() + timedelta(days=7)
response.set_cookie(
    key="user_token", 
    value="tkn_9876", 
    expires=expires_date, 
    path="/api",
    secure=True,
    samesite="Lax"
)


### 4. Redirects

```python
from virapi.response import redirect_response

# 302 Found (Temporary Redirect)
response = redirect_response("/new-path")

# 301 Moved Permanently
response = redirect_response("/new-path-permanent", status_code=301)
```