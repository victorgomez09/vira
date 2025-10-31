from vira.vira import Vira
from vira.request import Request
from vira.response import text_response

app = Vira(initial_state={"counter": 0, "db_url": "sqlite:///db.sqlite"})

@app.get("/")
async def index(request: Request):
    # Access the application state via app.state
    app.state.set("greeting", request.headers)
    return text_response(app.state.get("greeting", "Hello, World!"))

@app.get("/app-state")
async def app_state():
    # Access the application state via app.state
    return text_response(app.state.get("greeting", "Hello, World!"))

@app.get("/increment-counter")
async def increment_counter(request: Request):
    # Access the application state via request.app.state or request.state
    # Use the incr() atomic method if State implements it (in-process)
    request.state.set("counter", request.state.get("counter", 0) + 1)
    return text_response(f"counter incremented")

@app.get("/show-counter")
async def souw_counter(request: Request):
    # Access the application state via request.app.state or request.state
    # Use the incr() atomic method if State implements it (in-process)
    return text_response(f"counter={request.state.get('counter', 0)}")

@app.get("/value")
async def get_value(request: Request):
    # Read state attributes directly (similar to FastAPI)
    db_url = request.state.get("db_url", None)
    return text_response(f"db_url={db_url}")

@app.get("/aset")
async def aset_example(request: Request):
    # Asynchronous example if State implements async methods (aset/aget)
    if hasattr(request.state, "aset"):
        await request.state.aset("async_key", "value 123")
        val = await request.state.aget("async_key")
        return text_response(f"async_key={val}")
    return text_response("async methods not available on State")

# ============================================================================
# APPLICATION ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting Vira Complete Example")
    print("📍 Visit: http://localhost:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)