# vira/plugin.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vira import Vira # Previene la importación circular

class ViraPlugin:
    """Clase base para todos los plugins de Vira."""
    
    def __init__(self, app: 'Vira', **kwargs):
        self.app = app
        
    def register(self):
        """Método que se llama para inicializar el plugin y registrar handlers/rutas."""
        raise NotImplementedError("El método 'register' debe ser implementado por la subclase.")
