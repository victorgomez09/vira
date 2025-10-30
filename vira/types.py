from enum import Enum
from typing import TypeVar, Callable, Awaitable, Optional

BODY_TYPE = TypeVar('BODY_TYPE')
QUERY_STRING_TYPE = TypeVar('QUERY_STRING_TYPE')
HandlerType = Callable[['RequestData[QUERY_STRING_TYPE, BODY_TYPE]'], Awaitable['BaseHTTPResponse']]
QueryExtractor = Optional[Callable[[bytes], QUERY_STRING_TYPE]]
BodyExtractor = Optional[Callable[[bytes], BODY_TYPE]]
TaskHandlerType = Callable[['TaskParams'], Awaitable[None]]

class Methods(Enum):
    GET = 'GET'
    POST = 'POST'
    PUT = 'PUT'
    PATCH = 'PATCH'
    DELETE = 'DELETE'


class StatusCode:
    OK = 200
    BAD_REQUEST = 400
    NOT_FOUND = 404
    METHOD_NOT_ALLOWED = 405
    INTERNAL_SERVER_ERROR = 500