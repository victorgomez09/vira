# Add parent directory to path to import vira
import os
import sys
from typing import Union
from pydantic import BaseModel


sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from plugins.openapi.openapi import OpenAPIPlugin
from vira.vira import Vira
from vira.response import json_response

class UserCreate(BaseModel):
    """Pydantic model for user creation with validation."""
    username: str
    email: str
    age: int

app = Vira()
app.add_plugin(
    OpenAPIPlugin, 
    title="Complete Vira example API",
    description="This is a complete example API demonstrating Vira features.",
    version="1.0.0",
)

@app.post("/users")
async def create_user(user_data: UserCreate):
    """
    JSON Request Body validation and injection is handled by the framework using
    the UserCreate Pydantic model.
    """
    # El objeto user_data es una instancia de UserCreate, ya validada
    # user_data.age es garantizado ser un int
    
    return json_response(
        {
            "status": "success",
            "message": f"User '{user_data.username}' created and validated.",
            "details": {
                "email": user_data.email,
                "age": user_data.age,
                "age_type": type(user_data.age).__name__ # Debe ser 'int'
            }
        },
        status_code=201
    )

@app.get("/users/{user_id:int}")
async def get_user(user_id: int, q: Union[str, None] = None):
    """
    Path parameter validation is handled by the framework. The user_id is guaranteed to be an int.
    """
    
    return json_response(
        {
            "status": "success",
            "message": f"User '{user_id}' retrieved successfully.",
            "query": q
        },
        status_code=200
    )