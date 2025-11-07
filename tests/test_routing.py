"""
Test suite for virapi routing system.
Tests the Route, Router, APIRouter classes and decorator functionality.
"""

import pytest
from virapi import virapi, APIRouter, Route, Request, Response
from virapi.response import text_response, json_response
from virapi.testing import TestClient, TestRequest
from virapi.testing.response import TestResponse


class TestRoute:
    """Test the Route class."""

    def test_route_creation(self):
        async def handler(request: Request):
            return text_response("test")

        route = Route("/test", handler, methods={"GET"})
        assert route.path == "/test"
        assert route.handler == handler
        assert route.methods == {"GET"}

    def test_route_matches_exact_path(self):
        async def handler(request: Request):
            return text_response("test")

        route = Route("/test", handler, methods={"GET"})
        matches, params = route.matches("/test", "GET")
        assert matches == True
        assert params == {}

        matches, params = route.matches("/test", "POST")
        assert matches == False

        matches, params = route.matches("/other", "GET")
        assert matches == False

    def test_route_matches_default_methods(self):
        async def handler(request: Request):
            return text_response("test")

        # Test default methods (should be GET)
        route = Route("/test", handler)
        matches, params = route.matches("/test", "GET")
        assert matches == True
        assert params == {}

        matches, params = route.matches("/test", "POST")
        assert matches == False

    @pytest.mark.asyncio
    async def test_route_handle(self):
        async def handler(request: Request):
            return text_response("handled")

        route = Route("/test", handler, methods={"GET"})

        # Create a mock request object
        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
            "server": ("localhost", 8000),
            "scheme": "http",
        }

        async def mock_receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        request = Request(scope, mock_receive)
        await request.load_body()
        response = await route.handle(request)
        assert isinstance(response, Response)


class TestAPIRouter:
    """Test the APIRouter class."""

    def test_apirouter_creation(self):
        router = APIRouter()
        assert router.routes == []

    def test_apirouter_get_decorator(self):
        router = APIRouter()

        @router.get("/test")
        async def handler(request: Request):
            return text_response("test")

        assert len(router.routes) == 1
        assert router.routes[0].path == "/test"
        assert router.routes[0].methods == {"GET"}

    def test_apirouter_post_decorator(self):
        router = APIRouter()

        @router.post("/test")
        async def handler(request: Request):
            return text_response("test")

        assert len(router.routes) == 1
        assert router.routes[0].methods == {"POST"}

    def test_apirouter_multiple_methods(self):
        router = APIRouter()

        @router.route("/test", methods={"GET", "POST"})
        async def handler(request: Request):
            return text_response("test")

        assert len(router.routes) == 1
        assert router.routes[0].methods == {"GET", "POST"}


class TestFastASGI:
    """Test the virapi application with routing using TestClient."""

    def test_fastasgi_creation(self):
        app = virapi()
        assert isinstance(app.api_router, APIRouter)

    def test_fastasgi_get_decorator(self):
        app = virapi()

        @app.get("/test")
        async def handler(request: Request):
            return text_response("test")

        assert len(app.api_router.routes) == 1
        assert app.api_router.routes[0].path == "/test"
        assert app.api_router.routes[0].methods == {"GET"}

    def test_fastasgi_include_router(self):
        app = virapi()
        api_router = APIRouter()

        @api_router.get("/users")
        async def get_users(request: Request):
            return json_response({"users": []})

        app.include_router(api_router, prefix="/api")

        result = app.api_router.find_route("/api/users", "GET")
        assert result is not None
        route, params = result
        assert route.path == "/api/users"
        assert route.methods == {"GET"}

    def test_fastasgi_get_request(self):
        """Test GET request handling."""
        app = virapi()

        @app.get("/test")
        async def handler(request: Request):
            return text_response("success")

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        assert response.text() == "success"

    def test_fastasgi_post_request(self):
        """Test POST request handling."""
        app = virapi()

        @app.post("/echo")
        async def echo_handler(request: Request):
            await request.load_body()
            body = request.text()
            return text_response(f"Echo: {body}")

        client = TestClient(app)
        test_request = TestRequest().set_raw_body("Hello World")
        response = client.post("/echo", test_request)

        assert response.status_code == 200
        assert response.text() == "Echo: Hello World"

    def test_fastasgi_json_request(self):
        """Test JSON request handling."""
        app = virapi()

        @app.post("/json")
        async def json_handler(request: Request):
            await request.load_body()
            data = request.json()
            return json_response({"received": data})

        client = TestClient(app)
        test_data = {"name": "virapi", "version": "1.0"}
        test_request = TestRequest().set_json_body(test_data)
        response: TestResponse = client.post("/json", test_request)

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["received"]["name"] == "virapi"
        assert response_data["received"]["version"] == "1.0"


class TestRouteMatching:
    """Integration tests for the complete routing system using TestClient."""

    def test_complex_routing_scenario(self):
        """Test a complex scenario with multiple routers."""
        app = virapi()

        # Main app routes
        @app.get("/")
        async def home(request: Request):
            return text_response("home")

        @app.get("/hello")
        async def hello(request: Request):
            return text_response("Hello, World!")

        # API router
        api_router = APIRouter()

        @api_router.get("/users")
        async def get_users(request: Request):
            return json_response({"users": []})

        @api_router.post("/users")
        async def create_user(request: Request):
            await request.load_body()
            user_data = request.json()
            return json_response({"created": user_data, "id": 123})

        app.include_router(api_router, prefix="/api")

        client = TestClient(app)

        # Test home route
        response = client.get("/")
        assert response.status_code == 200
        assert response.text() == "home"

        # Test hello route
        response = client.get("/hello")
        assert response.status_code == 200
        assert response.text() == "Hello, World!"

        # Test API GET route with prefix
        response = client.get("/api/users")
        assert response.status_code == 200
        data = response.json()
        assert data == {"users": []}

        # Test API POST route with prefix
        user_data = {"name": "John Doe", "email": "john@example.com"}
        test_request = TestRequest().set_json_body(user_data)
        response = client.post("/api/users", test_request)
        assert response.status_code == 200
        data = response.json()
        assert data["created"] == user_data
        assert data["id"] == 123

        # Test non-existent route
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_multiple_http_methods(self):
        """Test different HTTP methods on the same path."""
        app = virapi()

        @app.get("/resource")
        async def get_resource(request: Request):
            return json_response({"method": "GET", "data": "resource"})

        @app.post("/resource")
        async def create_resource(request: Request):
            await request.load_body()
            data = request.json()
            return json_response({"method": "POST", "received": data})

        @app.put("/resource")
        async def update_resource(request: Request):
            await request.load_body()
            data = request.json()
            return json_response({"method": "PUT", "updated": data})

        @app.delete("/resource")
        async def delete_resource(request: Request):
            return json_response({"method": "DELETE", "deleted": True})

        client = TestClient(app)

        # Test GET
        response = client.get("/resource")
        assert response.status_code == 200
        assert response.json()["method"] == "GET"

        # Test POST
        post_data = {"name": "test"}
        test_request = TestRequest().set_json_body(post_data)
        response = client.post("/resource", test_request)
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "POST"
        assert data["received"] == post_data

        # Test PUT
        put_data = {"name": "updated"}
        test_request = TestRequest().set_json_body(put_data)
        response = client.put("/resource", test_request)
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "PUT"
        assert data["updated"] == put_data

        # Test DELETE
        response = client.delete("/resource")
        assert response.status_code == 200
        data = response.json()
        assert data["method"] == "DELETE"
        assert data["deleted"] is True

        """Test query parameter handling."""
        app = virapi()

        @app.get("/search")
        async def search(request: Request):
            query = request.query_params.get("q", "")
            limit = int(request.query_params.get("limit", "10"))
            return json_response({"query": query, "limit": limit})

        client = TestClient(app)

        # Create request with query parameters
        test_request = TestRequest().set_query_params(q="virapi", limit="20")
        response = client.get("/search", test_request)

        assert response.status_code == 200
        data = response.json()
        assert data["query"] == "virapi"
        assert data["limit"] == 20

    def test_route_ordering_and_conflicts(self):
        """Test that routes are matched in the order they were defined."""
        app = virapi()

        # More specific route should be defined first
        @app.get("/api/health")
        async def health_check(request: Request):
            return text_response("healthy")

        # Less specific route - note: virapi requires path parameters to be in handler signature
        @app.get("/api/{general:str}")
        async def general_api(request: Request, general: str):
            return text_response("general")

        client = TestClient(app)

        # Test that specific route is matched
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.text() == "healthy"

        # Test that general route works
        response = client.get("/api/general")
        assert response.status_code == 200
        assert response.text() == "general"

        # Test a truly unmatched route (different path structure)
        response = client.get("/different/path")
        assert response.status_code == 404


class TestPathParameterInjection:
    """Test path parameter injection into handler functions."""

    def test_string_parameter_injection(self):
        """Test injection of string path parameters."""
        app = virapi()

        @app.get("/users/{username:str}")
        async def get_user(request: Request, username: str):
            return text_response(f"User: {username}")

        client = TestClient(app)
        response = client.get("/users/john_doe")

        assert response.status_code == 200
        assert response.text() == "User: john_doe"

    def test_integer_parameter_injection(self):
        """Test injection of integer path parameters."""
        app = virapi()

        @app.get("/users/{user_id:int}")
        async def get_user_by_id(request: Request, user_id: int):
            return json_response({"user_id": user_id, "type": type(user_id).__name__})

        client = TestClient(app)
        response = client.get("/users/123")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 123
        assert data["type"] == "int"

    def test_float_parameter_injection(self):
        """Test injection of float path parameters."""
        app = virapi()

        @app.get("/products/{price:float}")
        async def get_product_by_price(request: Request, price: float):
            return json_response({"price": price, "type": type(price).__name__})

        client = TestClient(app)
        response = client.get("/products/19.99")

        assert response.status_code == 200
        data = response.json()
        assert data["price"] == 19.99
        assert data["type"] == "float"

    def test_multiple_parameters_injection(self):
        """Test injection of multiple path parameters."""
        app = virapi()

        @app.get("/users/{user_id:int}/posts/{post_id:int}")
        async def get_user_post(request: Request, user_id: int, post_id: int):
            return json_response(
                {
                    "user_id": user_id,
                    "post_id": post_id,
                    "message": f"User {user_id}, Post {post_id}",
                }
            )

        client = TestClient(app)
        response = client.get("/users/42/posts/123")

        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == 42
        assert data["post_id"] == 123
        assert data["message"] == "User 42, Post 123"

    def test_mixed_parameter_types(self):
        """Test injection of mixed parameter types."""
        app = virapi()

        @app.get("/store/{category:str}/item/{item_id:int}/price/{price:float}")
        async def get_item(request: Request, category: str, item_id: int, price: float):
            return json_response(
                {
                    "category": category,
                    "item_id": item_id,
                    "price": price,
                    "summary": f"{category} item #{item_id} costs ${price}",
                }
            )

        client = TestClient(app)
        response = client.get("/store/electronics/item/456/price/299.99")

        assert response.status_code == 200
        data = response.json()
        assert data["category"] == "electronics"
        assert data["item_id"] == 456
        assert data["price"] == 299.99
        assert data["summary"] == "electronics item #456 costs $299.99"

    def test_parameter_with_request_injection(self):
        """Test path parameters combined with Request injection."""
        app = virapi()

        @app.get("/api/{version:str}/users/{user_id:int}")
        async def versioned_user_api(request: Request, version: str, user_id: int):
            return json_response(
                {
                    "version": version,
                    "user_id": user_id,
                    "method": request.method,
                    "path": request.path,
                }
            )

        client = TestClient(app)
        response = client.get("/api/v1/users/789")

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "v1"
        assert data["user_id"] == 789
        assert data["method"] == "GET"
        assert data["path"] == "/api/v1/users/789"

    def test_invalid_integer_parameter(self):
        """Test error handling for invalid integer parameters."""
        app = virapi()

        @app.get("/users/{user_id:int}")
        async def get_user_by_id(request: Request, user_id: int):
            return json_response({"user_id": user_id})

        client = TestClient(app)
        response = client.get("/users/not_a_number")

        # Should return 404 because the route doesn't match due to type conversion failure
        assert response.status_code == 404

    def test_invalid_float_parameter(self):
        """Test error handling for invalid float parameters."""
        app = virapi()

        @app.get("/products/{price:float}")
        async def get_product_by_price(request: Request, price: float):
            return json_response({"price": price})

        client = TestClient(app)
        response = client.get("/products/invalid_price")

        # Should return 404 because the route doesn't match due to type conversion failure
        assert response.status_code == 404

    def test_parameter_order_independence(self):
        """Test that parameter order in handler signature doesn't matter."""
        app = virapi()

        @app.get("/test/{param1:str}/{param2:int}")
        async def handler_param_order(request: Request, param2: int, param1: str):
            # Note: param2 comes before param1 in signature
            return json_response({"param1": param1, "param2": param2})

        client = TestClient(app)
        response = client.get("/test/hello/42")

        assert response.status_code == 200
        data = response.json()
        assert data["param1"] == "hello"
        assert data["param2"] == 42

    def test_default_string_parameter_type(self):
        """Test that parameters without explicit type default to string."""
        app = virapi()

        @app.get("/items/{item_name}/{count}")  # No explicit :str type
        async def get_item(request: Request, item_name, count: str):
            return text_response(f"Item: {item_name}, Count: {count}")

        client = TestClient(app)
        response = client.get("/items/laptop/2")

        assert response.status_code == 200
        assert response.text() == "Item: laptop, Count: 2"

    def test_param_type_mismatch(self):
        """Test that type mismatches raise ValueError during route registration."""
        app = virapi()

        # This should raise a ValueError when the decorator is applied
        with pytest.raises(
            ValueError,
            match="Parameter 'item_id' type mismatch: route expects <class 'int'> but handler annotated as <class 'str'>",
        ):

            @app.get("/items/{item_id:int}")
            async def get_item(request: Request, item_id: str):
                return text_response(f"Item ID: {item_id}")


if __name__ == "__main__":
    pytest.main([__file__])
