# Uploaded File Container

## Overview

The `UploadFile` class is a container for metadata about a file uploaded via a `multipart/form-data` request. It provides a clean, safe interface for accessing, saving, and managing the lifecycle of the temporary file stored on disk.

## Key Components

| Component | Description |
| :--- | :--- |
| **`UploadFile`** (Class) | Container for file upload metadata and disk location. |
| **`filename`** | The original name of the file on the client's machine. |
| **`size`** | The size of the file in bytes. |
| **`content_type`** | The MIME type (e.g., `image/jpeg`). |
| **`open(mode='rb')`** | Provides a safe, **read-only** file handle for reading the content. |
| **`save(path)`** | Copies the temporary file to a permanent location. |
| **`cleanup()`** | Deletes the temporary file from the disk. |

## How to Use

You obtain instances of `UploadFile` from the `Request.files()` method.

### 1. Reading the File

```python
from vira.request import Request

@app.post("/upload")
async def process_file(request: Request):
    uploaded_files = await request.files()
    
    for upload_file in uploaded_files:
        print(f"Processing: {upload_file.filename} ({upload_file.content_type})")
        
        # Read the content safely
        with upload_file.open() as f:
            # Note: This is a file-like object
            content_bytes = f.read() 
```


### 2. Saving the File Permanently

```python
import os

@app.post("/upload")
async def save_file(request: Request):
    uploaded_files = await request.files()
    
    for upload_file in uploaded_files:
        # Create a permanent path
        storage_path = os.path.join("/app/permanent_storage", upload_file.filename)
        
        # The save() method handles the copy operation (shutil.copy2)
        upload_file.save(storage_path) 
        print(f"File saved to {storage_path}")
```

## Implementation Notes
- Read-Only Safety: The open() method validates the requested mode. If a write mode ('w', 'a', '+') is specified, it raises a ValueError to prevent accidental modification of the temporary file, encouraging the use of save() for permanent storage.

- Automatic Cleanup: The cleanup() method is designed to be called automatically by the parent Request object once the request-response cycle is complete, ensuring the temporary file is deleted even if the handler fails.

- get_path(): This method is available for advanced use cases where a library might require the raw file path for its own I/O, but its use bypasses the built-in read-only safety.