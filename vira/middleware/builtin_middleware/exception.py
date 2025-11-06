"""
Exception handling middleware for Vira.

Captures unhandled exceptions raised by downstream middleware or route handlers
and converts them into JSON responses. The level of detail in the JSON output
Mode-controlled output:
        mode="production":
                {"error": {"type": "HTTP_500_INTERNAL_SERVER_ERROR", "message": "Internal Server Error"}}
        mode="debug":
                {"error": {"type": "ValueError", "message": "Invalid value", "detail": "repr(...)", "traceback": "..."}}
"""

from __future__ import annotations

import traceback
from typing import Callable, Awaitable, Literal, TYPE_CHECKING
from ...response import json_response, Response
from ...status import HTTPStatus

if TYPE_CHECKING:  # pragma: no cover - only for type hints
    from ...request import Request


class ExceptionMiddleware:
    """Middleware that converts unhandled exceptions to JSON responses.

    Args:
            mode: Either "production" (default) for minimal messages or "debug" for full traceback.
    """

    def __init__(self, mode: Literal["production", "debug"] = "production"):
        self.mode = mode.lower()

    async def __call__(
        self, request: "Request", call_next: Callable[["Request"], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)
        except Exception as exc:  # noqa: BLE001 - we intentionally catch all
            if self.mode == "debug":
                tb = "".join(
                    traceback.format_exception(type(exc), exc, exc.__traceback__)
                )
                payload = {
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                        "detail": repr(exc),
                        "traceback": tb,
                    }
                }
            else:
                payload = {
                    "error": {
                        "type": HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR.name,
                        "message": "Internal Server Error",
                    }
                }

            return json_response(
                payload,
                status_code=HTTPStatus.HTTP_500_INTERNAL_SERVER_ERROR,
            )


__all__ = ["ExceptionMiddleware"]
