from queue import Queue
from enum import Enum

class Estado(Enum):
    SYNCING = 1
    ACTIVE = 2
    CLOSING = 3

class UserSession:
    def __init__(self, user_id, addr, sock):
        self.user_id = user_id
        self.addr = addr
        self.sock = sock
        self.queue = Queue()
        self.estado = Estado.SYNCING

    def set_estado(self, nuevo_estado):
        """Cambia el estado de la sesión. nuevo_estado debe ser una instancia de Estado."""
        if not isinstance(nuevo_estado, Estado):
            raise ValueError("nuevo_estado debe ser una instancia de Estado")
        self.estado = nuevo_estado

    def get_estado(self):
        """Devuelve el estado actual de la sesión."""
        return self.estado
