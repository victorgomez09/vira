# Content Security Policy

## Overview

The `CSPMiddleware` injects the **`Content-Security-Policy`** header into responses to mitigate common attacks like Cross-Site Scripting (XSS) and data injection. It enforces a list of trusted content sources (scripts, styles, images, etc.) for the browser.

## Initialization & Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`policy`** | `Dict[str, Union[str, list]]` | Strict Base | Dictionary defining the CSP directives and their allowed sources (e.g., `{"default-src": ["'self'"]}`). |
| **`report_uri`** | `str` | `None` | A URI where the browser should send JSON reports of any policy violations. |
| **`report_only`** | `bool` | `True` | If `True` (default), uses the header `Content-Security-Policy-Report-Only` (violations are logged but not blocked). If `False`, uses `Content-Security-Policy` (violations are strictly blocked). |

## Usage Example

```python
from virapi import virapi
from virapi.middleware.csp import CSPMiddleware

app = virapi()

# 1. Report-Only Mode (Development/Monitoring)
# A strict policy that logs violations but doesn't block them.
app.add_middleware(
    CSPMiddleware(
        policy={
            "default-src": ["'self'", "cdn.example.com"],
            "script-src": ["'self'", "apis.google.com"],
        },
        report_uri="/csp-reports",
        report_only=True # Header is 'Content-Security-Policy-Report-Only'
    )
)

# 2. Enforcement Mode (Production Blocking)
app.add_middleware(
    CSPMiddleware(
        policy={"default-src": ["'self'"]}, # Very strict: only same-origin resources allowed
        report_only=False # Header is 'Content-Security-Policy'
    )
)
```

## Implementation Notes
- Header Name: By default, it operates in monitoring mode, which is safer for deployment. The header name is changed based on the report_only parameter.

- Policy Building: The middleware automatically converts the Python policy dictionary into the semicolon-separated CSP string format.