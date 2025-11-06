from plugins.jwt.base import User
from plugins.jwt.decorators import jwt_authenticated_only, jwt_requires_role
from plugins.jwt.jwt import ViraJWTAuthPlugin
from vira import Vira
from vira.response import text_response

app = Vira()

app.add_plugin(
    ViraJWTAuthPlugin, 
    secret_key="your_very_secret_key_here", 
    algorithms=["HS256"]
)


@app.get("/public")
async def public_route():
    return text_response("This route is public.")

@app.get("/user/profile")
@jwt_authenticated_only
async def protected_route(request):
    # Here you can access the user attached by the plugin
    current_user: User = request.user
    return text_response(f"Welcome, {current_user.user_id}! You are authenticated.")

@app.get("/admin/panel")
@jwt_requires_role("admin")
async def admin_route():
    return text_response("Welcome to the Admin Panel.")