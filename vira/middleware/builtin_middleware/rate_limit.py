import time
from typing import Callable, Awaitable, Dict, Any, Tuple
from vira.request import Request
from vira.response import Response

# Placeholder type for the Redis client instance (e.g., redis.asyncio.Redis)
RedisClient = Any

class RateLimitMiddleware:
    """
    Middleware to implement rate limiting, supporting both distributed Redis 
    and single-process in-memory storage.

    Uses Redis's atomic operations when available for secure, distributed tracking.
    Falls back to in-memory tracking if no Redis client is provided.
    """

    def __init__(self, redis_client: RedisClient = None, limit: int = 100, window_seconds: int = 60):
        """
        Initializes the rate limit middleware.

        Args:
            redis_client: An initialized asynchronous Redis client instance (optional).
            limit: The maximum number of requests allowed in the window.
            window_seconds: The duration of the time window in seconds.
        """
        self.redis = redis_client
        self.limit = limit
        self.window_seconds = window_seconds
        
        # If no Redis client is provided, initialize an in-memory dictionary
        if self.redis is None:
            # In-memory store: {ip_address: {'count': int, 'reset_time': float}}
            self.requests: Dict[str, Dict[str, Any]] = {}
        # If Redis is used, self.requests remains None

    async def __call__(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        
        # 1. Get the client IP address
        # Assuming the Request object exposes client information like this:
        client_ip = request.client.host if hasattr(request, 'client') and hasattr(request.client, 'host') else 'unknown'
        
        now = time.time()
        current_count = 0
        reset_timestamp = 0
        retry_after = 0
        
        if self.redis:
            # --- REDIS MODE (Distributed) ---
            redis_key = f"rate_limit:{client_ip}"
            
            try:
                # Atomically increment the request count and get its TTL
                pipe = self.redis.pipeline()
                pipe.incr(redis_key)
                pipe.ttl(redis_key)
                results = await pipe.execute()
                
                current_count = results[0]
                ttl = results[1] # Time to Live in seconds
                
            except Exception as e:
                # If Redis connection fails, fail open (allow request) but log error
                print(f"RateLimiter Redis Error: {e}")
                return await call_next(request)

            # Set expiration time only if key is new (TTL is -1 or -2)
            if ttl < 0:
                # If key did not exist, INCR created it. Set its expiration now.
                await self.redis.expire(redis_key, self.window_seconds)
                ttl = self.window_seconds 
            
            retry_after = max(0, ttl)
            reset_timestamp = int(now + retry_after)

        else:
            # --- IN-MEMORY MODE (Single Process) ---
            client_data = self.requests.get(client_ip)

            if client_data is None or now > client_data['reset_time']:
                # First request or window expired: Reset the counter and the time window
                self.requests[client_ip] = {
                    'count': 1,
                    'reset_time': now + self.window_seconds
                }
                current_count = 1
                reset_timestamp = int(self.requests[client_ip]['reset_time'])
                # No need to proceed, request is always allowed here
                return await call_next(request) 
            
            # Increment and check the limit
            client_data['count'] += 1
            current_count = client_data['count']
            reset_timestamp = int(client_data['reset_time'])
            retry_after = max(0, int(client_data['reset_time'] - now))


        # 2. Check if the limit has been reached (Logic shared between Redis and In-Memory)
        if current_count > self.limit:
            # Limit reached: Return 429 Too Many Requests
            
            response = Response(
                status_code=429,
                content="Too Many Requests. Please try again later.",
                media_type="text/plain"
            )
            # Suggest when the client can retry
            response.headers["Retry-After"] = str(retry_after)
            # Add X-RateLimit headers for transparency
            response.headers["X-RateLimit-Limit"] = str(self.limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            response.headers["X-RateLimit-Reset"] = str(reset_timestamp)
            
            return response

        # 3. Request is allowed, proceed (Only reached in Redis mode and In-Memory after increment)
        
        # Execute the rest of the chain
        response = await call_next(request)
        
        # 4. Add X-RateLimit headers to allowed responses for transparency
        remaining = max(0, self.limit - current_count)
        
        response.headers["X-RateLimit-Limit"] = str(self.limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_timestamp)

        return response
