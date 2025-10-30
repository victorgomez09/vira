import json
from typing import (
    AsyncGenerator,
    Generic,
    Callable,
    Awaitable,
    Dict,
    Any,
    List,
    Tuple,
    Union,
)
from urllib.parse import unquote_plus

from vira.exceptions import InvalidRequestDataException
from vira.types import QUERY_STRING_TYPE, BODY_TYPE, BodyExtractor, QueryExtractor

class RequestData(Generic[QUERY_STRING_TYPE, BODY_TYPE]):

    def __init__(
        self,
        asgi_receiver_method: Callable[[], Awaitable[Dict[str, Any]]],
        headers: List[Tuple[bytes, bytes]],
        query_string: bytes = b"",
        qs_extractor: QueryExtractor = None,
        body_extractor: BodyExtractor = None,
    ):
        self._qs_extractor = qs_extractor
        self._body_extractor = body_extractor
        self._asgi_receiver_method = asgi_receiver_method

        self._body = b""
        self._headers = headers
        self._query_string = query_string

    async def get_query_string(self) -> Union[QUERY_STRING_TYPE, None]:
        """
        This method will trigger custom extractors registered withing the router
        The type of the returned value depends on the query_string_extractor used.

        If no extractor is registered, returns None.
        """
        if self._qs_extractor is None:
            return None
        return self._qs_extractor(self._query_string)

    async def get_query_string_dict(self) -> dict:
        """
        Parse the query string as Dict. Malformatted values will be ignored.

        !Important: it won't trigger custom extractors as query_string_extractor is not used

        You would probably want to use either parse_qs or parse_qsl from the urllib.parse STD package,
        but I wanted to build it just to show the process of parsing it here.
        """
        result = {}
        if not self._query_string:
            return result

        qs = self._query_string.replace(b"?", b"")
        for key_value_pair in qs.split(b"&"):
            infos = key_value_pair.split(b"=")
            if len(infos) != 2:
                # skip malformed values
                continue
            try:
                key = unquote_plus(infos[0].decode("utf-8"))
                value = unquote_plus(infos[1].decode("utf-8"))
                if key in result:
                    if not isinstance(result[key], list):
                        result[key] = [result[key]]
                    result[key].append(value)
                else:
                    result[key] = value
            except (UnicodeDecodeError, ValueError):
                continue  # Skip malformed values

        return result

    async def get_stream_body_bytes(self) -> AsyncGenerator[bytes, None]:
        """
        Streams the request body bytes. Can only be called once per request.
        After the first complete iteration, subsequent calls will yield the cached body.

        Note: This follows ASGI spec where the receiver callable is exhausted after
        the first complete read.
        """
        if self._body:
            yield self._body
            return

        has_more_data = True
        while has_more_data:
            message = await self._asgi_receiver_method()

            data = message.get("body", b"")
            if not data:
                break

            self._body += data
            yield data
            has_more_data = message.get("more_body", False)

    async def _load_all_body(self) -> bytes:
        if self._body:
            return self._body

        async for _ in self.get_stream_body_bytes():
            pass

        return self._body

    async def get_json_body(self) -> dict:
        """
        Parse the request body as JSON.
        Raises ValueError if contains invalid JSON.

        !Important: it won't trigger custom extractors as body_extractor is not used
        """
        body = await self._load_all_body()
        try:
            if not body:
                return {}
            return json.loads(body)
        except json.JSONDecodeError as e:
            raise InvalidRequestDataException(f"Invalid JSON body: {e}")

    async def get_body(self) -> Union[BODY_TYPE, None]:
        """
        This method will trigger custom extractors registered withing the router
        The type of the returned value depends on the body_extractor used.

        If no extractor is registered, returns None.
        """
        if self._body_extractor is None:
            return None

        body = await self._load_all_body()
        return self._body_extractor(body)

    async def get_headers(self) -> dict:
        return {
            key.decode("utf-8"): value.decode("utf-8") for key, value in self._headers
        }

    async def get_header_value(self, key: str) -> str:
        headers = await self.get_headers()
        return headers.get(key, "")
