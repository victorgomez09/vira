# virapi/plugin.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from virapi import virapi # Prevent circular import for type checking

class ViraPlugin:
    """Base class for all virapi plugins."""

    def __init__(self, app: 'virapi', **_):
        self.app = app
        
    def register(self):
        """Method called to initialize the plugin and register handlers/routes."""
        raise NotImplementedError("The 'register' method must be implemented by the subclass.")
