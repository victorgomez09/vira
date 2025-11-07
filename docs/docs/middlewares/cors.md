# CORS Middleware (Cross-Origin Resource Sharing)

## Overview

The `CORSMiddleware` handles [Cross-Origin Resource Sharing](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS) by adding the necessary `Access-Control-*` headers to responses. This allows browsers to permit requests from origins other than the server's own. It is designed to be compatible with the behavior of FastAPI's `CORSMiddleware`.

## Initialization & Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`allow_origins`** | `Sequence[str]` | `[]` | List of origins that are allowed to make cross-origin requests. Use `["*"]` to allow all origins. |
| **`allow_methods`** | `Sequence[str]` | `["GET"]` | List of allowed HTTP methods (e.g., `["GET", "POST"]`). Use `["*"]` for all standard methods. |
| **`allow_headers`** | `Sequence[str]` | `[]` | List of allowed HTTP request headers. If `["*"]` is used, the middleware automatically reflects headers requested in preflight requests. |
| **`allow_credentials`** | `bool` | `False` | Set to `True` to support credentials (cookies, HTTP authentication) in cross-origin requests. |
| **`expose_headers`** | `Sequence[str]` | `[]` | List of response headers that should be made accessible to the client (browser). |
| **`max_age`** | `int` | `600` | The maximum time (seconds) for which preflight requests can be cached by the browser. |

## Usage Example

```python
from virapi import virapi
from virapi.middleware.cors import CORSMiddleware

app = virapi()

app.add_middleware(
    CORSMiddleware(
        allow_origins=["[https://frontend.example.com](https://frontend.example.com)", "http://localhost:8080"],
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Authorization", "Content-Type"],
        allow_credentials=True,
        max_age=1200,  # Cache preflight for 20 minutes
    )
)

# Alternative: Allow all origins and all methods
app.add_middleware(
    CORSMiddleware(
        allow_origins=["*"],
        allow_methods=["*"],
    )
)
```

## Implementation Notes
- Preflight Requests: The middleware automatically handles OPTIONS requests by responding with the appropriate Access-Control-* headers and a 200 OK status.

- Origin Matching: Uses regex matching if allow_origin_regex is provided.