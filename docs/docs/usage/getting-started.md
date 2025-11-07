# virapi Framework

The **virapi** framework is a simple, modern, and ASGI-compatible Python microframework, designed for educational purposes and lightweight API development.

***

## 1. Getting Started: The Basic Application

The core of a virapi application is a single `virapi` class instance, which acts as the main entry point and the central hub for routing, middleware, and state management.

### `main.py`

```python
# main.py
from virapi import virapi
from virapi.response import text_response
from virapi.request import Request # Recommended for type hinting

# 1. Instantiate the virapi application
app = virapi()

# 2. Define a simple route using the @app.get decorator
@app.get("/")
async def homepage(request: Request):
    """The root endpoint of the API."""
    # Handlers must return a Response object
    return text_response("Hello from virapi!")

# To run the application, use an ASGI server like Uvicorn:
# $ uvicorn main:app
```
### Application Configuration
You can configure the application on initialization, managing resources like temporary file storage and shared application state.

| Parameter | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| max_in_memory_file_size | int | 1024 * 1024 (1MB) | Max size in bytes a file is kept in memory before being streamed to disk during upload. |
| temp_dir | Optional[str] | None | Directory for temporary files. None uses the system default. |
| initial_state | Optional[Dict] | None | Dictionary of initial, thread-safe values available via app.state. |

```python
app = virapi(
    max_in_memory_file_size=5 * 1024 * 1024, # 5 MB in memory
    initial_state={"app_version": "1.0.0", "db_pool": None}
)
```


## 2. Routing and Dynamic Parameters
virapi uses an APIRouter to register routes corresponding to HTTP methods.

### Route Decorators and HTTP Methods
Routes are registered using method-specific decorators:

| Decorator | HTTP Method |
| :--- | :--- |
| @app.get(path) | GET |
| @app.post(path) | POST |
| @app.put(path) | PUT |
| @app.delete(path) | DELETE |
| @app.route(path, methods={...}) | Custom Methods |

### Path Parameter Type Conversion
Dynamic segments are defined using {name:type} syntax. The framework automatically converts the URL segment into the specified Python type.

| Type Hint | Python Type | Example Match |
| :--- | :--- | :--- |
| :int | int | /users/123 |
| :str | str | /items/apple |
| :uuid | uuid.UUID | /resource/a1b2c3d4... |
| :multipath | str | Matches all remaining segments |

```python
@app.get("/users/{user_id:int}")
async def get_user_by_id(user_id: int): 
    # user_id is guaranteed to be an integer
    return json_response({"message": f"Fetching user {user_id}"})

@app.post("/files/{filepath:multipath}")
async def serve_file(filepath: str):
    # filepath will be a full path like 'images/photo.jpg'
    return text_response(f"File path received: {filepath}")
```

## 3. Request Handling (Request Object)
The ```Request``` object provides asynchronous access to all incoming request data.

### Retrieving Request Body Data
Handler functions must be async as body parsing is an asynchronous operation.

| Data Type | Access Method | Example |
| :--- | :--- | :--- |
| Query Params | request.query_params | limit = request.query_params.get("limit") |
| Headers | request.headers | auth = request.headers.get("Authorization") |
| JSON Body | await request.json() | data = await request.json() |
| Form Data | await request.form() | username = await request.form().get("user") |
| Uploaded Files | await request.files() | files = await request.files() |

### File Upload Example
File uploads are handled via multipart/form-data. The parser uses temporary files for safety and memory efficiency.

```python
from virapi.request import Request
from virapi.response import json_response
from virapi.request.upload_file import UploadFile

@app.post("/upload/document")
async def handle_document_upload(request: Request):
    # Retrieve all files from the multipart body
    uploaded_files: list[UploadFile] = await request.files() 
    
    if not uploaded_files:
        return json_response({"error": "No file uploaded"}, status_code=400)
    
    file = uploaded_files[0]
    
    # Safely read content using a context manager
    with file.open(mode="rb") as f:
        # Check the file header or process chunk-by-chunk
        pass 
        
    # Persist the file to a permanent location
    save_path = f"/storage/{file.filename}"
    file.save(save_path) # Uses shutil.copy2 internally
    
    # The temporary file is automatically cleaned up after the request finishes
    return json_response({
        "message": "File uploaded and saved",
        "filename": file.filename,
        "size": file.size
    })
```

## 4. Response Creation
Handlers must return an object of the Response class. Helper functions are provided for common formats.

| Helper Function | Content-Type | Purpose |
| :--- | :--- | :--- |
| text_response(content, ...) | text/plain | Simple string responses. |
| html_response(content, ...) | text/html | Responses rendering as web pages. |
| json_response(content, ...) | application/json | Standard API responses. |
| redirect_response(url, ...) | N/A (3xx status) | Redirects the client to a new URL. |

```python
from virapi.status import HTTPStatus
from virapi.response import json_response, redirect_response

@app.get("/status")
async def check_status():
    # Use the HTTPStatus Enum for clarity
    return json_response(
        {"server": "operational"},
        status_code=HTTPStatus.HTTP_200_OK 
    )

@app.get("/go-to-docs")
async def redirect_user():
    # Permanently move the resource (301)
    return redirect_response("/docs", status_code=HTTPStatus.HTTP_301_MOVED_PERMANENTLY)
```

## 5. Middleware and Security
Middleware are functions or classes that form an "onion" chain around your route handlers. They are executed in the order they are added.

### Adding MiddlewareMiddleware are added to the ```app.middleware_chain```.

```python
from virapi.middleware.exception import ExceptionMiddleware # Handles errors
from virapi.middleware.cors import CORSMiddleware # Cross-Origin Resource Sharing
from virapi.middleware.g_zip import GZipMiddleware # Compresses responses
from virapi.middleware.trusted_host import TrustedHostMiddleware # Prevents host header attacks

# The order matters! ExceptionMiddleware should be added first to catch errors from everything below it.
app.middleware_chain.add(ExceptionMiddleware(mode="debug")) # Full tracebacks in debug mode
app.middleware_chain.add(TrustedHostMiddleware(allowed_hosts=["localhost", "*.myservice.com"]))
app.middleware_chain.add(CORSMiddleware(
    allow_origins=["[http://frontend.com](http://frontend.com)"],
    allow_methods=["GET", "POST"],
))
app.middleware_chain.add(GZipMiddleware(minimum_size=1024)) # Compress if response > 1KB
```

### Security Middleware Highlights

| Middleware | Feature |
| :--- | :--- |
| HttpHeadersMiddleware | Adds X-Frame-Options, X-Content-Type-Options, Referrer-Policy, and HSTS headers. |
| CSPMiddleware | Injects the Content-Security-Policy header to mitigate XSS. |
| HTTPSRedirectMiddleware | Forces HTTP requests to be redirected to HTTPS using a 307 temporary redirect. |
| RateLimitMiddleware | Implements rate limiting per IP address, supporting in-memory or Redis storage. |

## 6. Application State (State Object)
The State object is a thread-safe, dictionary-like container available at two levels:

1- Application State (app.state): Global, shared resources (e.g., database pool, cache client).

2- Request State (request.state): Request-scoped data, often used to pass information from a middleware (e.g., the authenticated user) to the handler.

Example: Using State

```python
# main.py - Setup
app = virapi(initial_state={"request_count": 0})

# Middleware Example
async def request_counter(request: Request, call_next):
    # Increment global count (synchronous access)
    request.app.state.incr("request_count") # Assuming an atomic incr method
    
    # Store data for the handler (request-scoped)
    request.state.client_ip = request.client_ip 
    return await call_next(request)

app.middleware_chain.add(request_counter)

# Handler Example
@app.get("/info")
async def get_info(request: Request):
    global_count = await request.app.state.aget("request_count") # Asynchronous read
    client_ip = request.state.client_ip # Read request-scoped data
    
    return json_response({
        "total_requests": global_count,
        "current_ip": client_ip,
    })
```