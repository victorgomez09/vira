# HTTP Status Codes

## Overview

This module provides a comprehensive list of standard HTTP status codes wrapped in a Python `IntEnum`. This allows for highly readable code by using descriptive names instead of raw integer codes.

## Key Component

| Component | Description |
| :--- | :--- |
| **`HTTPStatus`** (IntEnum) | A class containing all standard HTTP status codes, inheriting from `enum.IntEnum`. |

## How to Use

Simply import `HTTPStatus` and use its members for response status codes. It automatically converts to an integer when passed to the `Response` class.

```python
from vira.status import HTTPStatus
from vira.response import text_response, json_response

# 200 Success
response_ok = text_response("OK", status_code=HTTPStatus.HTTP_200_OK)

# 201 Created
response_created = json_response({"id": 1}, status_code=HTTPStatus.HTTP_201_CREATED)

# 404 Not Found
response_not_found = text_response("Resource not found", status_code=HTTPStatus.HTTP_404_NOT_FOUND)

# 500 Server Error
response_error = text_response("Server failed", status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR)

# You can still use it as an integer
assert int(HTTPStatus.HTTP_404_NOT_FOUND) == 404
```