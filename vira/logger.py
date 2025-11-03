import logging
import os
import json
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, Dict

# ANSI color codes
COLOR_CODES = {
    "DEBUG": "\033[36m",     # Cyan
    "INFO": "\033[32m",      # Green
    "WARNING": "\033[33m",   # Yellow
    "ERROR": "\033[31m",     # Red
    "CRITICAL": "\033[41m",  # Red background
    "RESET": "\033[0m",      # Reset
}

# ------------------ FORMATTERS ------------------

class JSONFormatter(logging.Formatter):
    """Custom formatter for structured (JSON) logs."""
    def __init__(self, default_context: Optional[Dict[str, str]] = None, show_environment: bool = True):
        super().__init__()
        self.default_context = default_context or {}
        self.show_environment = show_environment

    def format(self, record):
        log_record = {
            "timestamp": datetime.utcfromtimestamp(record.created).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
        }

        # Merge default and dynamic context
        context = {**self.default_context}
        if hasattr(record, "request_id"):
            context["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            context["user_id"] = record.user_id
        if self.show_environment and hasattr(record, "environment"):
            context["environment"] = record.environment

        if context:
            log_record["context"] = context

        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_record)


class TextFormatter(logging.Formatter):
    """Human-readable text formatter."""
    def __init__(self, default_context: Optional[Dict[str, str]] = None, show_environment: bool = False, colored: bool = True):
        super().__init__(
            fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        self.default_context = default_context or {}
        self.show_environment = show_environment
        self.colored = colored

    def format(self, record):
        if self.colored and record.levelname in COLOR_CODES:
            color = COLOR_CODES[record.levelname]
            record.levelname = f"\u001b[1m{color}{record.levelname}{COLOR_CODES['RESET']}\u001b[0m"
            # record.name = f"\033[3m{record.name}\033[23m"
            
        base = super().format(record)
        context = []

        if hasattr(record, "request_id"):
            context.append(f"request_id={record.request_id}")
        if hasattr(record, "user_id"):
            context.append(f"user_id={record.user_id}")
        if self.show_environment and hasattr(record, "environment"):
            context.append(f"env={record.environment}")

        for key, value in self.default_context.items():
            context.append(f"{key}={value}")

        if context:
            base += " " + " ".join(context)
        return base


# ------------------ LOGGER CLASS ------------------

class EnvironmentLoggerAdapter(logging.LoggerAdapter):
    """
    A LoggerAdapter that automatically injects 'environment' into every log record.
    """
    def __init__(self, logger, environment: str):
        super().__init__(logger, {"environment": environment})

    def process(self, msg, kwargs):
        # Merge any existing extras with environment info
        extra = kwargs.get("extra", {})
        extra["environment"] = self.extra["environment"]
        kwargs["extra"] = extra
        return msg, kwargs


class Logger:
    """
    Configurable application logger that supports JSON or text output,
    file or console handlers, and contextual metadata.
    """

    def __new__(
        cls,
        name: str,
        log_file: Optional[str] = None,
        level: int = logging.INFO,
        max_bytes: int = 5_000_000,
        backup_count: int = 3,
        json_logs: bool = True,
        to_console: bool = True,
        environment: str = "production",
        default_context: Optional[Dict[str, str]] = None,
        show_environment: bool = False,
        colored_console: bool = True,
    ) -> logging.Logger:
        """
        Returns a configured logger instance directly.
        """
        instance = super(Logger, cls).__new__(cls)
        base_logger = instance._create_logger(
            name=name,
            log_file=log_file,
            level=level,
            max_bytes=max_bytes,
            backup_count=backup_count,
            json_logs=json_logs,
            to_console=to_console,
            default_context=default_context,
            show_environment=show_environment,
            colored_console=colored_console,
        )

        # Wrap with adapter to inject environment automatically
        return EnvironmentLoggerAdapter(base_logger, environment)

    def _create_logger(
        self,
        name: str,
        log_file: Optional[str],
        level: int,
        max_bytes: int,
        backup_count: int,
        json_logs: bool,
        to_console: bool,
        default_context: Optional[Dict[str, str]],
        show_environment: bool,
        colored_console: bool,
    ) -> logging.Logger:
        """Internal method to configure and return the base logger."""
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = False

        # Avoid duplicate handlers if logger is re-created
        if logger.handlers:
            logger.handlers.clear()

        default_context = default_context or {}

        formatter = (
            JSONFormatter(default_context, show_environment, colored_console)
            if json_logs
            else TextFormatter(default_context, show_environment, colored_console)
        )

        # File handler
        if log_file:
            os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
            file_handler = RotatingFileHandler(
                log_file, maxBytes=max_bytes, backupCount=backup_count
            )
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        # Console handler
        if to_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        return logger
