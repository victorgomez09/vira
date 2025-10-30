from vira.http_responses import (
    BAD_REQUEST_TEXTResponse,
    BaseHTTPResponse,
    METHOD_NOT_ALLOWED_TEXTResponse,
    NOT_FOUND_TEXTResponse,
)


class InvalidRequest(Exception):
    def __init__(self):
        super().__init__()
        self.http_response: BaseHTTPResponse = None  # just to help with type hinting


class InvalidRequestDataException(InvalidRequest):
    def __init__(self, message: str):
        super().__init__()
        self.http_response = BAD_REQUEST_TEXTResponse(message)


class NotFoundException(InvalidRequest):
    def __init__(self, message: str = "Not found"):
        super().__init__()
        self.http_response = NOT_FOUND_TEXTResponse(message)


class MethodNotAllowedException(InvalidRequest):
    def __init__(self, message: str = "Method not allowed"):
        super().__init__()
        self.http_response = METHOD_NOT_ALLOWED_TEXTResponse(message)
