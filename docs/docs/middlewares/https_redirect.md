# HTTPS Redirect Middleware

## Overview

The `HTTPSRedirectMiddleware` enforces the use of HTTPS for all traffic. If an incoming request uses the `http://` scheme, the middleware intercepts it and issues a permanent redirection to the equivalent `https://` URL.

## Initialization & Parameters

The middleware takes no configuration parameters.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **(None)** | - | - | The middleware uses a `307 Temporary Redirect` status code. |

## Usage Example

```python
from virapi import virapi
from virapi.middleware.https_redirect import HTTPSRedirectMiddleware

app = virapi()

# Add the middleware before any route handlers or other processing
# to ensure HTTP requests are immediately redirected.
app.add_middleware(HTTPSRedirectMiddleware())

# Request flow:
# 1. User requests [http://example.com/api](http://example.com/api)
# 2. Middleware redirects with 307 to [https://example.com/api](https://example.com/api)
# 3. User agent makes a new request to the HTTPS URL
```

## Implementation Notes
- Status Code: It uses 307 Temporary Redirect. While 301 Moved Permanently is often used for redirects, 307 is generally safer for programmatic redirects as it ensures the HTTP method (e.g., POST) is not accidentally changed to GET by the client on the second request.

- Redirect Logic: The middleware checks request.url.startswith("https://"). If it's not HTTPS, it performs a simple string replacement on the URL (http:// to https://) and returns the redirect response.