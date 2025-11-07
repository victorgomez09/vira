from plugins.oauth2.oauth2 import ViraOAuth2Plugin, oauth_session_required
from virapi import Virapi
from virapi.response import text_response

app = Virapi()

app.add_plugin(
    ViraOAuth2Plugin,
    client_id="CLIENT_ID_DE_GOOGLE",
    client_secret="SECRET_DE_GOOGLE",
    auth_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    userinfo_url="https://www.googleapis.com/oauth2/v3/userinfo",
    redirect_uri="http://localhost:8000/oauth/callback"
)

@app.get("/")
async def homepage():
    return text_response("Welcome! Go to <a href='/protected'>/protected</a> or <a href='/oauth/login'>/oauth/login</a>.")

@app.get("/protected")
@oauth_session_required
async def protected_route(request):
    current_user = request.user 
    return text_response(f"¡Ruta protegida por OAuth! User ID: {current_user.user_id}")