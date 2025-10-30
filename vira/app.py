from asyncio import get_running_loop, sleep
from typing import List, Dict, Any, Callable, Awaitable

from vira.api_router import ApiRouter
from vira.exceptions import InvalidRequest
from vira.http_responses import _ResponseData, BaseHTTPResponse, INTERNAL_SERVER_ERROR_TEXTResponse, NOT_FOUND_TEXTResponse
from vira.request_data import RequestData
from vira.router import Router
from vira.background_tasks import _create_background_tasks_instance

# ASGI type aliases
ASGIScope = Dict[str, Any]
ASGIReceive = Callable[[], Awaitable[Dict[str, None]]]
ASGISend = Callable[[Dict[str, Any]], Awaitable[None]]


class Vira:

    def __init__(self, max_running_tasks: int = 2):
        self._router = None
        self._bg_tasks = _create_background_tasks_instance(max_running_tasks=max_running_tasks)

    # Every time a request comes to server, the server will call the __call__ method of the class
    # The __call__ method is the entry point of the application
    async def __call__(self, scope, receive, send) -> None:
        # scope - it holds the requestr information as path, query strings, headers, etc... in this case a dict var
        # receive - its an async generator that yields the request body
        # send - its an async function that send the response back to the client
        if scope["type"] == "http":
            return await self._handle_http_request(scope, receive, send)

        if scope["type"] == "lifespan":
            return await self._handle_lifespan(receive, send)

    def include_routes(self, routes: List[ApiRouter]) -> None:
        """
        This method will add all registered routes to the application router.
        It should be called at the application startup.
        Call it twice will raise an error.

        e.g:
        # pkg1
        router_1 = ApiRouter()
        @router_1.get("/home")
        async def home(request_data):
            print("home triggered")

        @router_1.get("/")
        async def root(request_data):
            print("root triggered")

        # pkg2
        router_2 = ApiRouter()
        @router_2.get("/about")
        async def about(request_data):
            print("about triggered")

        app = Vira()
        app.include_routes([router_1, router_2])

        """
        assert self.router is None, "include_routes method can be called only once"

        if self.router is not None:
            return

        self.router = Router()

        route_list = []
        for router_items in routes:
            route_list += router_items.routes

        sorted_routes = sorted(route_list, key=lambda x: x[0])
        for route in sorted_routes:
            self.router.add_route(*route)

    async def _handle_http_request(
        self, scope: ASGIScope, receive: ASGIReceive, send: ASGISend
    ):
        """payload ref
        scope = {
            'type': 'http',
            'asgi': {'version': '3.0', 'spec_version': '2.3'},
            'http_version': '1.1', 'server': ('127.0.0.1', 8000),
            'client': ('127.0.0.1', 51945), 'scheme': 'http',
            'method': 'GET', 'root_path': '',
            'path': '/some-path/', 'raw_path': b'/some-path/',
            'query_string': b'qs1=1&qs2=opa!',
            'headers': [
                (b'user-agent', b'PostmanRuntime/7.45.0'),
                (b'accept', b'*/*'),
                (b'postman-token', b'1111f6f3-1111-1111-1111-37150dd41111'),
                (b'host', b'localhost:8000'),
                (b'accept-encoding', b'gzip, deflate, br'),
                (b'connection', b'keep-alive')
            ],
            'state': {}
        }
        """
        assert scope["type"] == "http"
        
        response_data = await self._run_http_handler(
            scope["path"], scope["method"], receive
        )
        await self._send_http_response(response_data, send)
    
    async def _run_http_handler(self, path: str, method: str, receive: ASGIReceive) -> _ResponseData:
        try:
            target = self.router.get_route(path, method)
            if target is None:
                return await NOT_FOUND_TEXTResponse()()

            request_data = RequestData(receive, target.query_string_extractor, target.body_extractor)
            response = await target.handler(request_data)
            if response is not isinstance(response, BaseHTTPResponse):
                print('handler returned a non valid response. Response must be an instance of BaseHTTPResponse')
                return await INTERNAL_SERVER_ERROR_TEXTResponse()()

            return await response()

        except InvalidRequest as e:
             return await e.http_response()

        except Exception as e:
            print('error' + str(e))
            return await INTERNAL_SERVER_ERROR_TEXTResponse()()
        
    @staticmethod
    async def _send_http_response(resp: _ResponseData, send: ASGISend):
        await send({
            "type": "http.response.start",
            "status": resp.status_code,
            "headers": resp.headers
        })

        await send({
            "type": "http.response.body",
            "body": resp.body
        })
        
    async def _handle_lifespan(
        self, receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]]
    ):
        async def run_bg_tasks():
            while True:
                await self._bg_tasks.run_tasks()
                await sleep(0.5)

        running_loop = get_running_loop()
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                running_loop.create_task(run_bg_tasks())
                await send({"type": "lifespan.startup.complete"})

            elif message["type"] == "lifespan.shutdown":
                await self._bg_tasks.shutdown()
                await send({"type": "lifespan.shutdown.complete"})
                return


vira = Vira()
