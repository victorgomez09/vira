# Request Object

## Overview

The `Request` class is a high-level abstraction over the low-level ASGI `scope` and `receive` callable. It provides convenient, property-based access to common HTTP request information and async methods to parse the request body in various formats.

## Key Components

| Component | Description |
| :--- | :--- |
| **`Request`** (Class) | Central object for accessing all incoming HTTP data. |
| **`method`**, **`path`**, **`headers`** | Properties for fundamental request data. |
| **`query_params`** | A dictionary-like object of URL query string parameters. |
| **`json()`** | Async method to read and parse the request body as JSON. |
| **`form()`** | Async method to read and parse URL-encoded form data. |
| **`files()`** | Async method to read and parse `multipart/form-data`, returning a list of `UploadFile` objects. |
| **`cleanup_files()`** | Deletes any temporary files created during file upload processing. |

## How to Use

### 1. Basic Access

```python
from virapi.request import Request
from virapi.response import text_response

async def handler(request: Request):
    method = request.method
    path = request.path
    auth_header = request.headers.get("Authorization")
    query_q = request.query_params.get("q", "default")
    
    return text_response(f"Method: {method}, Path: {path}, Query: {query_q}")


### 2. Reading Request Body (JSON/Form)
These methods are asynchronous and should be awaited. The body is read and cached on the first call.

```python
# For POST request with Content-Type: application/json
@app.post("/data")
async def handle_json(request: Request):
    data = await request.json()
    return json_response({"received": data})

# For POST request with Content-Type: application/x-www-form-urlencoded
@app.post("/data")
async def handle_form(request: Request):
    form_data = await request.form()
    return text_response(f"Name: {form_data['name']}")
```


### 3. Handling File Uploads
When the content type is multipart/form-data, use files() to get file data and form() to get simple fields.

```python
# For POST request with Content-Type: multipart/form-data
@app.post("/upload")
async def handle_upload(request: Request):
    uploaded_files = await request.files()
    form_data = await request.form()
    
    for upload_file in uploaded_files:
        # Save the temporary file permanently
        upload_file.save(f"/permanent/storage/{upload_file.filename}")
        
    return text_response(f"Uploaded {len(uploaded_files)} files.")
```

## Implementation Notes
- Lazy Body Parsing: The body is only read from the ASGI channel (via _receive_complete_message) and parsed (via json(), form(), etc.) when the corresponding method is called for the first time, improving performance for requests without a body.

- Cleanup: The Request class maintains a weakref.WeakSet of active requests and ensures that all temporary UploadFile objects are cleaned up via a finalizer (__del__) or when the main virapi app explicitly calls cleanup_files().