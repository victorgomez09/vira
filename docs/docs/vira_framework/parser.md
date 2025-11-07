# Multipart Parser

## Overview

The `MultipartParser` is a non-streaming implementation designed to parse `multipart/form-data` request bodies, which are typically used for file uploads. It separates text fields from file data, temporarily storing file contents on disk.

## Key Component

| Component | Description |
| :--- | :--- |
| **`MultipartParser`** (Class) | Handles the complex parsing of `multipart/form-data` content. |
| **`parse(body, boundary)`** | The main parsing method. Takes the raw byte body and boundary string, and returns a tuple of `(form_data: dict, uploaded_files: list[UploadFile])`. |
| **`extract_boundary(content_type)`** | Static method to extract the unique boundary string from the `Content-Type` header. |
| **`temp_dir`** | Directory where temporary upload files are stored. |

## How to Use

This class is typically used internally by the `Request.files()` method, but can be used manually if needed.

### 1. Parsing

```python
from virapi.multipart.parser import MultipartParser

# Example: Get content_type header from request
content_type = "multipart/form-data; boundary=----WebKitFormBoundaryABC123" 
boundary = MultipartParser.extract_boundary(content_type) # -> "----WebKitFormBoundaryABC123"

# Assume 'raw_body' is the full request body as bytes
parser = MultipartParser()
form_data, uploaded_files = parser.parse(raw_body, boundary)

# Form fields are in the dict
print(form_data["username"]) # -> "john_doe"

# Files are in the list of UploadFile objects
for upload_file in uploaded_files:
    print(upload_file.filename)
    with upload_file.open() as f:
        # read file content
        content = f.read()
```

## Implementation Notes
- Non-Streaming: The entire request body (body: bytes) is read into memory before parsing. This makes it unsuitable for very large file uploads due to memory limitations, but simplifies the parsing logic.

- Temporary Files: When a file part is encountered, its content is immediately written to a unique file in the temporary directory (managed by tempfile), and an UploadFile object is created to point to it.

- Cleanup: It relies on the consumer (the Request object) to ensure the UploadFile objects call their cleanup() method to delete the temporary files after the request is processed.