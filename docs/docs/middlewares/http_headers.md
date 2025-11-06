# Http Headers Middleware (Security Headers)

## Overview

The `HttpHeadersMiddleware` automatically injects a set of recommended, security-focused HTTP headers into every response. This helps protect against various client-side attacks, even if the application code is clean.

## Default Security Headers

The middleware includes these headers by default:

| Header | Purpose | Default Value |
| :--- | :--- | :--- |
| **`X-Frame-Options`** | Prevents clickjacking by disallowing framing. | `DENY` |
| **`X-Content-Type-Options`** | Prevents MIME-type sniffing. | `nosniff` |
| **`X-XSS-Protection`** | Enables the browser's native XSS filter. | `1; mode=block` |
| **`Referrer-Policy`** | Controls how much referrer information is sent. | `strict-origin-when-cross-origin` |

## Initialization & Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`headers`** | `dict` | `None` | Optional dictionary to override or add custom headers to the default set. |
| **`enable_hsts`** | `bool` | `True` | Whether to enable the `Strict-Transport-Security` (HSTS) header. |
| **`hsts_max_age`** | `int` | `31536000` | The `max-age` value (seconds) for the HSTS header (1 year). |

## Usage Example

```python
from vira import Vira
from vira.middleware.http_headers import HttpHeadersMiddleware

app = Vira()

# 1. Default Setup (recommended for most apps)
app.add_middleware(HttpHeadersMiddleware())

# 2. Customizing Headers and Disabling HSTS
app.add_middleware(
    HttpHeadersMiddleware(
        # Override Referrer-Policy and add a custom header
        headers={
            "Referrer-Policy": "no-referrer", 
            "X-App-Version": "1.2.3"
        },
        enable_hsts=False # Disable HSTS if you don't use HTTPS on all subdomains
    )
)
```

## Implementation Notes
- HSTS Requirement: The Strict-Transport-Security header is only added to a response if the incoming request scheme is https.