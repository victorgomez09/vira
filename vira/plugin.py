# vira/plugin.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vira import Vira # Prevent circular import for type checking

class ViraPlugin:
    """Base class for all Vira plugins."""

    def __init__(self, app: 'Vira', **_):
        self.app = app
        
    def register(self):
        """Method called to initialize the plugin and register handlers/routes."""
        raise NotImplementedError("The 'register' method must be implemented by the subclass.")
