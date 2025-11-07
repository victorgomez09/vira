# Trusted Host Middleware

## Overview

The `TrustedHostMiddleware` is a security measure that protects against HTTP Host header attacks. It strictly validates the `Host` header of the incoming request against a list of explicitly allowed domains. If the header does not match an allowed host, the request is blocked with a `400 Bad Request` response.

## Initialization & Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`allowed_hosts`** | `List[str]` | `None` | A list of host patterns that are permitted. |

## Host Pattern Examples

| Pattern | Matches |
| :--- | :--- |
| `["*"]` | Allows any host header (disables validation). |
| `["example.com"]` | Only matches `example.com`. |
| `["*.example.com"]` | Matches any subdomain, e.g., `www.example.com`, `api.example.com`, but *also* `example.com` itself. |
| `["localhost:8000"]` | Matches the host with a specific port. |

## Usage Example

```python
from virapi import virapi
from virapi.middleware.trusted_host import TrustedHostMiddleware

app = virapi()

# Enforce host validation for production deployment
app.add_middleware(
    TrustedHostMiddleware(
        allowed_hosts=[
            "production.myapp.com",
            "[www.production.myapp.com](https://www.production.myapp.com)",
            "localhost:8000"  # Allow local development host
        ]
    )
)

# Request flow:
# 1. Host: production.myapp.com -> Allowed
# 2. Host: hacker-site.com -> Blocked (400 Bad Request)
# 3. Host: api.production.myapp.com -> Blocked (only explicit hosts allowed)

# Example allowing all subdomains:
app.add_middleware(
    TrustedHostMiddleware(
        allowed_hosts=["*.mysite.com"]
    )
)
```

## Implementation Notes
- Blocking Behavior: If the Host header is missing or does not match any pattern, the middleware returns a 400 Bad Request response with the body "Invalid host header".

- Wildcard Logic: The check for *.domain ensures that if the host ends with .domain (e.g., sub.domain), it is allowed. It also explicitly allows the naked domain (e.g., domain).