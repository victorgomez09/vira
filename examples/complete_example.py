"""
Vira Complete Example

This example demonstrates the core features of Vira:
- Routing with path parameters
- Query strings, form data, and file uploads
- Middleware usage
- Cookies handling

To run this application:
    uvicorn complete_example:app --reload --host 0.0.0.0 --port 8000
"""

import sys
import os

# Add parent directory to path to import vira
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from vira import Vira, Request, APIRouter
from vira.response import text_response, json_response
from vira.middleware.builtin_middleware import CORSMiddleware, ExceptionMiddleware

# Create the main application
app = Vira()

# ============================================================================
# 1. BASIC MIDDLEWARE SETUP
# ============================================================================

# Add middleware
app.add_middleware(ExceptionMiddleware(mode="debug"))
app.add_middleware(
    CORSMiddleware(
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
)


# Custom logging middleware
async def logging_middleware(request: Request, call_next):
    print(f"🔍 {request.method} {request.path}")
    response = await call_next(request)
    print(f"✅ Response: {response.status_code}")
    return response


app.add_middleware(logging_middleware)

# Create API router
api_router = APIRouter()

# ============================================================================
# 2. BASIC ROUTING AND PATH PARAMETERS
# ============================================================================


@app.get("/")
async def home(request: Request):
    """Welcome page."""
    return text_response(
        """
🚀 Vira Complete Example

Available endpoints:
• GET  /users/{user_id}     - Get user by ID (path parameter)
• GET  /search?q=term       - Search with query parameters  
• POST /users               - Create user (JSON data)
• POST /upload              - Upload files
• GET  /cookies/set         - Set cookies
• GET  /cookies/get         - Get cookies
• GET  /api/health          - API health check
    """
    )


@app.get("/users/{user_id:int}")
async def get_user(request: Request, user_id: int):
    """Get user by ID - demonstrates path parameters with type conversion."""
    return json_response(
        {
            "user_id": user_id,
            "name": f"User {user_id}",
            "type": type(user_id).__name__,
            "path": request.path,
        }
    )


@app.get("/users/{username:str}")
async def get_user_by_name(request: Request, username: str):
    """Get user by username - demonstrates string path parameters."""
    return json_response(
        {
            "username": username,
            "display_name": username.title(),
            "type": type(username).__name__,
        }
    )


# ============================================================================
# 3. QUERY PARAMETERS
# ============================================================================


@app.get("/search")
async def search(request: Request):
    """Search endpoint - demonstrates query parameter handling."""
    query = request.query_params.get("q", "")
    limit = int(request.query_params.get("limit", "10"))
    offset = int(request.query_params.get("offset", "0"))

    results = []
    if query:
        # Simulate search results
        for i in range(offset, offset + limit):
            results.append(
                {
                    "id": i,
                    "title": f"Result {i} for '{query}'",
                    "relevance": max(0.1, 1.0 - (i * 0.1)),
                }
            )

    return json_response(
        {
            "query": query,
            "results": results,
            "pagination": {"limit": limit, "offset": offset, "total": len(results)},
        }
    )


# ============================================================================
# 4. JSON DATA AND FORM DATA
# ============================================================================


@app.post("/users")
async def create_user(request: Request):
    """Create user - demonstrates JSON request body handling."""
    await request.load_body()

    try:
        user_data = request.json()
        # Simulate user creation
        new_user = {
            "id": 123,
            "name": user_data.get("name", "Unknown"),
            "email": user_data.get("email", ""),
            "created": "2025-09-17T12:00:00Z",
        }
        return json_response(new_user, status_code=201)
    except Exception as e:
        return json_response({"error": str(e)}, status_code=400)


@app.post("/contact")
async def contact_form(request: Request):
    """Contact form - demonstrates form data handling."""
    await request.load_body()

    form_data = request.form
    return json_response(
        {
            "message": "Form submitted successfully",
            "data": {
                "name": form_data.get("name", ""),
                "email": form_data.get("email", ""),
                "message": form_data.get("message", ""),
            },
        }
    )


# ============================================================================
# 5. FILE UPLOADS
# ============================================================================


@app.post("/upload")
async def upload_file(request: Request):
    """File upload - demonstrates file handling."""
    await request.load_body()

    files = request.files
    uploaded_files = []

    for upload_file in files:
        file_info = {
            "filename": upload_file.filename,
            "content_type": upload_file.content_type,
            "size": upload_file.size,
        }
        uploaded_files.append(file_info)

    form_data = request.form

    return json_response(
        {
            "message": f"Uploaded {len(uploaded_files)} file(s)",
            "files": uploaded_files,
            "form_data": dict(form_data),
        }
    )


# ============================================================================
# 6. COOKIES
# ============================================================================


@app.get("/cookies/set")
async def set_cookies(request: Request):
    """Set cookies - demonstrates cookie handling."""
    response = json_response({"message": "Cookies set successfully"})

    # Set various types of cookies
    response.set_cookie("user_id", "12345")
    response.set_cookie("session_token", "abc123xyz", httponly=True)
    response.set_cookie("theme", "dark", max_age=86400)  # 1 day

    return response


@app.get("/cookies/get")
async def get_cookies(request: Request):
    """Get cookies - demonstrates reading cookies."""
    cookies = dict(request.cookies)

    return json_response(
        {
            "message": "Here are your cookies",
            "cookies": cookies,
            "cookie_count": len(cookies),
        }
    )


# ============================================================================
# 7. API ROUTER USAGE
# ============================================================================


@api_router.get("/health")
async def health_check(request: Request):
    """API health check."""
    return json_response(
        {"status": "healthy", "version": "1.0.0", "timestamp": "2025-09-17T12:00:00Z"}
    )


@api_router.get("/info")
async def api_info(request: Request):
    """API information."""
    return json_response(
        {
            "name": "Vira Complete API",
            "version": "1.0.0",
            "endpoints": ["GET /api/health", "GET /api/info"],
        }
    )


# Include the API router with prefix
app.include_router(api_router, prefix="/api")

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Vira Complete Example")
    print("📍 Visit: http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
