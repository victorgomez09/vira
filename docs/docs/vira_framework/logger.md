# Custom Logging

## Overview

This module implements a custom logging configuration for the virapi framework, featuring two primary formatters: **`JSONFormatter`** for structured, machine-readable logs, and **`TextFormatter`** for human-readable, colored console output. The `Logger` class acts as a central facade to set up the logging system.

## Key Components

| Component | Description |
| :--- | :--- |
| **`JSONFormatter`** | Formatter that serializes log records into a JSON object, ideal for log aggregation systems. Includes `timestamp`, `level`, `logger`, `message`, and optional `context` data (`request_id`, `user_id`). |
| **`TextFormatter`** | Formatter for console output with ANSI color codes based on log level (e.g., DEBUG=Cyan, ERROR=Red). |
| **`Logger`** (Class) | Manages the configuration of Python's built-in `logging` module. Supports rotating file logs and console output. |

## How to Use

### 1. Initialization and Configuration

The `Logger` class should be instantiated once, typically at application startup.

```python
from virapi.logger import Logger, logging

# Initialize the logger with configuration
app_logger = Logger().setup(
    name="virapi",
    log_file="app.log",
    level=logging.INFO, # Only INFO and above to file
    json_logs=False, # Use TextFormatter for files
    to_console=True,
    colored_console=True,
    default_context={"environment": "production"},
)

### 2. Logging
Use the returned standard Python logger instance.

```python
# Get the configured logger
log = logging.getLogger("virapi")

# Standard log messages
log.info("Application starting up...")
log.error("Failed to connect to external service.", exc_info=True)

# Logging with dynamic context (for JSONFormatter)
log_record = log.makeRecord(
    name="virapi",
    level=logging.INFO,
    fn="handler",
    lno=10,
    msg="Request processed successfully",
    args=(),
    exc_info=None
)
# Injecting custom attributes that the JSONFormatter can pick up
log_record.request_id = "req_12345"
log_record.user_id = 99
log.handle(log_record)
```

## Implementation Details
- Rotating File Handler: If log_file is provided, a RotatingFileHandler is used to manage log file size and rotation (max_bytes, backup_count).

- Console Handler: An logging.StreamHandler is used for console output.

- Context Merging (JSON): The JSONFormatter merges default_context (from setup) with dynamic attributes attached to the log record (like request_id), providing rich, structured logging data.