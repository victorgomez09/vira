# virapi Examples

This folder contains a comprehensive example demonstrating all core virapi features.

## complete_example.py

A single, comprehensive example that demonstrates:

- **Routing**: Basic GET/POST routes with decorators
- **Path Parameters**: Type conversion (`{user_id:int}`, `{username:str}`)

### 🚀 **Core Features**

- **Routing**: Path parameters with type conversion (`/users/{user_id:int}`)
- **HTTP Methods**: GET, POST with proper request handling
- **Query Parameters**: Search functionality with pagination
- **Request Bodies**: JSON data and form data handling
- **File Uploads**: Multipart form data with file handling
- **Cookies**: Setting and reading cookies
- **API Router**: Organized routes with prefixes

### 🛡️ **Middleware**

- **Built-in Middleware**: CORS and Exception handling
- **Custom Middleware**: Simple logging middleware example
- **Middleware Ordering**: Proper middleware stack setup

### 🏃‍♂️ **Running the Example**

```bash
# From the virapi root directory
uvicorn examples.complete_example:app --reload --port 8000
```

Then visit: http://localhost:8000

### 📚 **Learning Path**

This single example is designed to show you:

1. How to set up a virapi application
2. Basic and advanced routing patterns
3. Handling different types of request data
4. Adding middleware for cross-cutting concerns
5. Organizing routes with APIRouter

For more advanced middleware patterns, authentication strategies, and complex routing scenarios, please refer to the documentation.
