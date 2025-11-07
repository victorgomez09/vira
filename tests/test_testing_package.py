"""
Comprehensive tests for the virapi testing package.

These tests verify that TestClient produces correct results by comparing
with live HTTP server responses using the 'requests' library.
"""

import hashlib
import threading
import time

import pytest
import requests
import uvicorn

from virapi import virapi, Request
from virapi.response import json_response
from virapi.testing import TestClient, TestRequest


class TestApp:
    """Test virapi application with various endpoints for testing."""

    def __init__(self):
        self.app = virapi()
        self._setup_routes()

    def _setup_routes(self):
        """Set up test routes that return request information."""

        @self.app.get("/simple")
        async def simple_get():
            return json_response({"method": "GET", "path": "/simple"})

        @self.app.post("/echo")
        async def echo_post(request: Request):
            body = request.body()
            headers = dict(request.headers)

            return json_response(
                {
                    "method": "POST",
                    "path": "/echo",
                    "headers": headers,
                    "body": body.decode() if body else "",
                    "query_params": dict(request.query_params),
                }
            )

        @self.app.put("/json")
        async def json_put(request: Request):
            try:
                json_data = request.json()
            except:
                json_data = None

            return json_response(
                {
                    "method": "PUT",
                    "path": "/json",
                    "json_data": json_data,
                    "content_type": request.headers.get("content-type", ""),
                }
            )

        @self.app.post("/upload")
        async def file_upload(request: Request):
            files_info = []
            form_data = {}

            # Process uploaded files
            for upload_file in request.files:
                # Calculate hash of the entire file content for integrity verification
                file_hash = hashlib.sha256()
                with upload_file.open() as f:
                    # Read in chunks to handle large files efficiently
                    while chunk := f.read(8192):
                        file_hash.update(chunk)

                files_info.append(
                    {
                        "filename": upload_file.filename,
                        "content_type": upload_file.content_type,
                        "size": upload_file.size,
                        "content_hash": file_hash.hexdigest(),
                    }
                )

            # Process form fields
            for key, value in request.form.items():
                form_data[key] = value

            return json_response(
                {
                    "method": "POST",
                    "path": "/upload",
                    "files": files_info,
                    "form_data": form_data,
                    "content_type": request.headers.get("content-type", ""),
                }
            )

        @self.app.post("/multipart")
        async def multipart_data(request: Request):
            return json_response(
                {
                    "method": "POST",
                    "path": "/multipart",
                    "files": [
                        {
                            "filename": f.filename,
                            "content_type": f.content_type,
                            "size": f.size,
                        }
                        for f in request.files
                    ],
                    "form_fields": dict(request.form),
                    "content_type": request.headers.get("content-type", ""),
                }
            )


class LiveServerHelper:
    """Helper for managing a live virapi server during tests."""

    def __init__(self, app: virapi, host: str = "127.0.0.1", port: int = 8765):
        self.app = app
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.server = None
        self.server_thread = None

    def start(self):
        """Start the server in a background thread."""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="critical",  # Minimize logging during tests
            access_log=False,
        )
        self.server = uvicorn.Server(config)

        self.server_thread = threading.Thread(target=self.server.run, daemon=True)
        self.server_thread.start()

        # Wait for server to start
        max_retries = 50  # 5 seconds max
        for _ in range(max_retries):
            try:
                response = requests.get(f"{self.base_url}/simple", timeout=0.1)
                if response.status_code == 200:
                    break
            except (requests.ConnectionError, requests.Timeout):
                time.sleep(0.1)
                continue
        else:
            raise RuntimeError("Failed to start test server")

    def stop(self):
        """Stop the server."""
        if self.server:
            self.server.should_exit = True
        if self.server_thread:
            self.server_thread.join(timeout=2)

    def make_request(self, method: str, path: str, **kwargs):
        """Make an HTTP request to the live server."""
        url = f"{self.base_url}{path}"
        response = requests.request(method, url, **kwargs)

        # Convert to our expected format
        try:
            json_data = response.json()
        except:
            json_data = None

        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "body": response.content,
            "json": json_data,
        }


class TestTestingPackage:
    """Test cases comparing TestClient with live HTTP server responses."""

    @pytest.fixture
    def test_app(self):
        """Create test virapi application."""
        return TestApp().app

    @pytest.fixture
    def test_client(self, test_app):
        """Create TestClient instance."""
        return TestClient(test_app)

    @pytest.fixture
    def live_server(self, test_app):
        """Create and manage live server for HTTP requests."""
        helper = LiveServerHelper(test_app)
        helper.start()
        yield helper
        helper.stop()

    def compare_responses(self, test_response, http_response):
        """Compare TestClient response with live HTTP server response."""
        # Compare status codes
        assert test_response.status_code == http_response["status_code"]

        # Compare JSON responses
        test_json = test_response.json()
        http_json = http_response["json"]

        # For this basic comparison, just check core data matches
        # (ignoring headers and content_type which may have server differences)
        test_core = {
            k: v for k, v in test_json.items() if k not in ["headers", "content_type"]
        }
        http_core = {
            k: v for k, v in http_json.items() if k not in ["headers", "content_type"]
        }

        assert test_core == http_core

    def test_simple_get(self, test_client, live_server):
        """Test simple GET request without parameters."""
        # TestClient request
        test_response = test_client.get("/simple")

        # Live HTTP server request
        http_response = live_server.make_request("GET", "/simple")

        self.compare_responses(test_response, http_response)

    def test_put_with_json(self, test_client, live_server):
        """Test PUT request with JSON body."""
        test_data = {"name": "John", "age": 30, "active": True}

        # TestClient request
        test_req = TestRequest().set_json_body(test_data)
        test_response = test_client.put("/json", test_req)

        # Live HTTP server request
        http_response = live_server.make_request(
            "PUT", "/json", headers={"content-type": "application/json"}, json=test_data
        )

        self.compare_responses(test_response, http_response)

    def test_post_with_form_data(self, test_client, live_server):
        """Test POST request with form data and query parameters."""
        form_data = {"message": "Hello World", "user": "test"}
        params = {"format": "json"}

        # TestClient request
        test_req = TestRequest().set_form_data(**form_data).set_query_params(**params)
        test_response = test_client.post("/echo", test_req)

        # Live HTTP server request
        http_response = live_server.make_request(
            "POST",
            "/echo",
            data=form_data,
            params=params,
        )

        self.compare_responses(test_response, http_response)

    def test_single_file_upload(self, test_client, live_server):
        """Test single file upload with multipart/form-data."""
        file_content = "Hello, this is a test file content!"
        filename = "test_file.txt"

        # TestClient request
        test_req = TestRequest().upload_file(
            "document", filename, file_content, "text/plain"
        )
        test_response = test_client.post("/upload", test_req)

        # Live HTTP server request
        files = {"document": (filename, file_content, "text/plain")}
        http_response = live_server.make_request("POST", "/upload", files=files)

        self.compare_responses(test_response, http_response)

    def test_multiple_file_upload(self, test_client, live_server):
        """Test multiple file upload with different content types."""
        # TestClient request
        test_req = (
            TestRequest()
            .upload_file("doc1", "readme.txt", "This is a README file", "text/plain")
            .upload_file("doc2", "data.json", '{"key": "value"}', "application/json")
            .upload_file("doc3", "image.jpg", b"\x89PNG\r\n\x1a\n", "image/jpeg")
        )
        test_response = test_client.post("/upload", test_req)

        # Live HTTP server request
        files = {
            "doc1": ("readme.txt", "This is a README file", "text/plain"),
            "doc2": ("data.json", '{"key": "value"}', "application/json"),
            "doc3": ("image.jpg", b"\x89PNG\r\n\x1a\n", "image/jpeg"),
        }
        http_response = live_server.make_request("POST", "/upload", files=files)

        self.compare_responses(test_response, http_response)

    def test_file_upload_with_form_data(self, test_client, live_server):
        """Test file upload combined with regular form fields."""
        file_content = "CSV data: name,age\nJohn,30\nJane,25"
        form_data = {"description": "User data export", "format": "csv"}

        # TestClient request
        test_req = (
            TestRequest()
            .upload_file("datafile", "users.csv", file_content, "text/csv")
            .set_form_data(**form_data)
        )
        test_response = test_client.post("/upload", test_req)

        # Live HTTP server request
        files = {"datafile": ("users.csv", file_content, "text/csv")}
        http_response = live_server.make_request(
            "POST", "/upload", files=files, data=form_data
        )

        self.compare_responses(test_response, http_response)

    def test_large_file_upload(self, test_client, live_server):
        """Test uploading a larger file to verify handling."""
        # Create a larger file content (10KB)
        large_content = "Large file content. " * 500  # ~10KB
        filename = "large_file.txt"

        # TestClient request
        test_req = TestRequest().upload_file("largefile", filename, large_content)
        test_response = test_client.post("/upload", test_req)

        # Live HTTP server request - specify content type to match TestClient behavior
        files = {"largefile": (filename, large_content, "text/plain")}
        http_response = live_server.make_request("POST", "/upload", files=files)

        self.compare_responses(test_response, http_response)

    def test_multipart_with_special_characters(self, test_client, live_server):
        """Test multipart handling with special characters in filenames and content."""
        filename = "tëst_fílé_with_ñümbërs_123.txt"
        file_content = "Content with special chars: ñáéíóú, emoji: 🎉, and unicode: ℃"
        form_data = {"notes": "Special characters in form: ñáéíóú"}

        # TestClient request
        test_req = (
            TestRequest()
            .upload_file("special_file", filename, file_content)
            .set_form_data(**form_data)
        )
        test_response = test_client.post("/multipart", test_req)

        # Live HTTP server request - specify content type to match TestClient behavior
        files = {"special_file": (filename, file_content, "text/plain")}
        http_response = live_server.make_request(
            "POST", "/multipart", files=files, data=form_data
        )

        self.compare_responses(test_response, http_response)
