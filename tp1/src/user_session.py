import queue
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
        self.queue = queue.Queue()
        self.estado = Estado.SYNCING

    def set_estado(self, estado):
        self.estado = estado

    def get_estado(self):
        return self.estado