# Rate Limit Middleware

## Overview

The `RateLimitMiddleware` protects your application from abuse or DDoS attacks by limiting the number of requests a client (identified by IP address) can make within a specified time window. When a client exceeds the limit, it receives a `429 Too Many Requests` response.

## Initialization & Parameters

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| **`redis_client`** | Any | `None` | An initialized **asynchronous Redis client** instance. If provided, rate limiting is distributed and atomic. |
| **`limit`** | `int` | `100` | The maximum number of requests allowed per client in the window. |
| **`window_seconds`** | `int` | `60` | The duration of the time window in seconds. |

## Usage and Storage

### 1. In-Memory Mode (Single Process)

If `redis_client` is `None`, the middleware uses a simple in-memory dictionary. This mode is **not suitable for multi-process deployments** (like Uvicorn/Gunicorn with multiple workers) as limits are not shared.

```python
from vira import Vira
from vira.middleware.rate_limit import RateLimitMiddleware

app = Vira()
# 10 requests per 60 seconds, non-distributed
app.add_middleware(
    RateLimitMiddleware(
        limit=10, 
        window_seconds=60
    )
)
```

### 2. Redis Mode (Distributed and Atomic)

If a Redis client is passed, the middleware uses Redis's atomic operations for accurate, synchronized rate limiting across all worker processes.

```python
from vira import Vira
from vira.middleware.rate_limit import RateLimitMiddleware
# Assuming you have an async Redis client initialized
# e.g., import redis.asyncio as redis; redis_client = redis.Redis(...) 

app = Vira()
app.add_middleware(
    RateLimitMiddleware(
        redis_client=your_redis_client_instance,
        limit=500, 
        window_seconds=300 # 500 requests per 5 minutes
    )
)
```

## Response Headers

When a request is processed (whether allowed or blocked), the middleware adds standard rate limiting headers for client transparency:

| Header | Description |
| :--- | :--- |
| X-RateLimit-Limit | The maximum requests allowed in the window. |
| X-RateLimit-Remaining | The number of requests remaining in the current window. |
| X-RateLimit-Reset | The timestamp (Unix epoch) when the current window resets. |
| Retry-After | Only on 429 response: The number of seconds to wait before retrying. |