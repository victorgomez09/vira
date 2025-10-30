import json
from dataclasses import dataclass
from typing import Any, Optional, Tuple, List

from vira.types import StatusCode


@dataclass
class _ResponseData:
    status_code: StatusCode
    body: bytes
    headers: list[tuple[bytes, bytes]]


class BaseHTTPResponse:

    def __init__(
        self,
        body: Any,
        status_code: StatusCode = StatusCode.OK,
        headers: Optional[dict] = None,
        encode: str = "utf-8",
    ):
        if headers is None:
            headers = {}
        assert isinstance(headers, dict), "headers must be a dict"
        assert isinstance(status_code, StatusCode) or isinstance(
            status_code, int
        ), "status_code must be a StatusCode enum or int"
        assert isinstance(encode, str), "encode must be a string"

        self._status_code = status_code
        self._headers = headers
        self._body = body
        self._encode = encode

    def __repr__(self):
        return f"<BaseHTTPResponse status_code={self._status_code}>"

    def get_headers(self) -> dict:
        return self._headers

    def get_status_code(self) -> StatusCode:
        return self._status_code

    def _get_bytes_headers(self) -> List[Tuple[bytes, bytes]]:
        headers = []
        for key, value in self._headers.items():
            headers.append((key.encode(self._encode), value.encode(self._encode)))

        return headers

    def add_header(self, key: str, value: str) -> None:
        self._headers[key] = value

    def get_body(self) -> bytes:
        raise NotImplementedError("get_body method is not implemented yet")

    async def __call__(self) -> _ResponseData:
        await self._set_body_length()
        headers = self._get_bytes_headers()

        return _ResponseData(self._status_code, self.get_body(), headers)

    async def _set_body_length(self):
        body_length = len(self.get_body())
        self._headers["content-length"] = str(body_length)


class TextResponse(BaseHTTPResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._headers["content-type"] = "text/plain"

    def get_body(self) -> bytes:
        if not self._body:
            return b""
        return self._body.encode(self._encode)


class JsonResponse(BaseHTTPResponse):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._headers["content-type"] = "application/json"

    def get_body(self) -> bytes:
        if not self._body:
            return b""
        return json.dumps(self._body).encode(self._encode)


def NOT_FOUND_JSONResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> JsonResponse:
    return JsonResponse(body, StatusCode.NOT_FOUND, headers, encode)


def BAD_REQUEST_JSONResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> JsonResponse:
    return JsonResponse(body, StatusCode.BAD_REQUEST, headers, encode)


def INTERNAL_SERVER_ERROR_JSONResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> JsonResponse:
    return JsonResponse(body, StatusCode.INTERNAL_SERVER_ERROR, headers, encode)


def OK_JSONResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> JsonResponse:
    return JsonResponse(body, StatusCode.OK, headers, encode)


def NOT_FOUND_TEXTResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> TextResponse:
    return TextResponse(body, StatusCode.NOT_FOUND, headers, encode)


def BAD_REQUEST_TEXTResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> TextResponse:
    return TextResponse(body, StatusCode.BAD_REQUEST, headers, encode)


def METHOD_NOT_ALLOWED_TEXTResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> TextResponse:
    return TextResponse(body, StatusCode.METHOD_NOT_ALLOWED, headers, encode)


def INTERNAL_SERVER_ERROR_TEXTResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> TextResponse:
    return TextResponse(body, StatusCode.INTERNAL_SERVER_ERROR, headers, encode)


def OK_TEXTResponse(
    body: Any = None, headers: Optional[dict] = None, encode: str = "utf-8"
) -> TextResponse:
    return TextResponse(body, StatusCode.OK, headers, encode)
