# GZip Middleware (Compression)

## Overview

The `GZipMiddleware` automatically compresses response bodies using `gzip` if the client's browser indicates support via the `Accept-Encoding` header. This reduces network bandwidth usage and can improve load times for text-based content.

## Initialization & Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`minimum_size`** | `int` | `500` | The minimum size (in bytes) a response body must be to be considered for compression. Small files are typically not worth compressing. |
| **`compresslevel`** | `int` | `9` | The compression level, from 0 (no compression) to 9 (highest compression, slowest process). |

## Compression Criteria

The middleware will only compress a response if all the following are true:
1.  The client's `Accept-Encoding` header includes `gzip`.
2.  The response does not already have a `Content-Encoding` header.
3.  The response `Content-Type` is text-based (e.g., `text/*`, `application/json`, `application/javascript`, `application/xml`).
4.  The response body size is greater than or equal to `minimum_size`.

## Usage Example

```python
from vira import Vira
from vira.middleware.g_zip import GZipMiddleware
from vira.response import json_response

app = Vira()

# Compress all responses larger than 1KB (1024 bytes)
app.add_middleware(
    GZipMiddleware(
        minimum_size=1024,
        compresslevel=6 # A good balance between speed and compression
    )
)

@app.get("/large-data")
async def get_large_data():
    # This dictionary will be converted to JSON and then compressed if > 1KB
    large_payload = {"items": [f"item_{i}" for i in range(1000)]}
    return json_response(large_payload)