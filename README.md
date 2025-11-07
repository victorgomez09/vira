# virapi 🚀

A lightweight and fast ASGI web framework built from scratch with FastAPI-inspired design.

## ✨ Features

- 🔗 **FastAPI-Style API**: Familiar decorators (`@app.get`, `@app.post`) and patterns
- 🎯 **Advanced Routing**: Path parameters with type conversion (`{id:int}`, `{name:str}`)
- 🔧 **Modular Design**: Organize code with `APIRouter` and prefixes
- 🛠️ **Middleware System**: Request/response pipeline with built-in middleware
- 📡 **ASGI 3.0 Compatible**: Works with uvicorn, hypercorn, and other ASGI servers
- 🔄 **Full Request/Response**: JSON, forms, file uploads, cookies, headers
- 🧪 **Testing Framework**: Built-in test client for easy endpoint testing
- 📚 **Excellent Documentation**: Every component is thoroughly documented

## 🚀 Quick Start

```python
from virapi import Virapi, json_response

app = Virapi()

@app.get("/")
async def home(request):
    return json_response({"message": "Hello, virapi!"})

@app.get("/users/{user_id:int}")
async def get_user(user_id: int, request):
    return json_response({"user_id": user_id, "type": type(user_id).__name__})

# Run with: uvicorn main:app --reload
```

## 🏗️ Architecture Overview

```
virapi/
├── virapi.py          # Main application class
├── request/             # Request handling & file uploads
├── response.py          # Response building & content types
├── routing/             # Advanced routing system
├── middleware/          # Middleware chain & built-ins
├── testing/             # Test client & utilities
└── status.py           # HTTP status codes
```

## 📚 Learn More

- **[Complete Documentation](docs/README.md)** - Detailed guides and examples
- **[Routing Guide](docs/ROUTING_GUIDE.md)** - Advanced routing patterns
- **[Middleware Guide](docs/MIDDLEWARE_GUIDE.md)** - Custom middleware development
- **[Examples](examples/)** - Real-world application examples

## 🛠️ Installation & Development

```bash
# Clone the repository
git clone https://github.com/victorgomez09/virapi.git
cd virapi

# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run examples
python examples/complete_example.py
```

## 🤝 Contributing

This is an educational project! Contributions that improve code clarity, add educational value, or enhance documentation are especially welcome.

## 📄 License

MIT License - Feel free to use this code for learning and teaching!
