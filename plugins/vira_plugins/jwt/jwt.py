from plugins.jwt.base import set_jwt_config
from vira.plugin import ViraPlugin
from typing import TYPE_CHECKING, List, Optional

if TYPE_CHECKING:
    from vira import Vira # Ensure typing only at type-check time

class ViraJWTAuthPlugin(ViraPlugin):
    """
    Plugin for Vira that implements JWT authentication with PyJWT.
    """
    def __init__(
        self, 
        app: 'Vira', 
        secret_key: str, 
        algorithms: Optional[List[str]] = None, 
        **kwargs
    ):
        super().__init__(app, **kwargs)
        self.secret_key = secret_key
        self.algorithms = algorithms

    def register(self):
        """
        Initializes the global security configuration.
        """
        if not self.secret_key:
            raise ValueError("ViraJWTAuthPlugin requires 'secret_key' during initialization.")

        # 1. Set up the internal validation logic of the plugin
        set_jwt_config(self.secret_key, self.algorithms)

        # 2. Optional: Attach the decorators to the Vira app object for easy access
        # (This allows the user to use app.auth.authenticated_only)
        # self.app.auth = self # If you decide to add a namespace to the app object

        print("ViraJWTAuthPlugin initialized successfully.")

# --- Key Exports for the User ---
# The end user will import this directly from the plugin package
__all__ = [
    "ViraJWTAuthPlugin", 
    "User", 
    "jwt_authenticated_only", 
    "jwt_requires_role"
]