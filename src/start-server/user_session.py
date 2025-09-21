# Definición de flags para operación
OP_UPLOAD = 0
OP_DOWNLOAD = 1

# Definición de flags para estado de sesión
STATE_CONNECTING = 0
STATE_ACTIVE = 1
STATE_DISCONNECTING = 2
STATE_CONNECTION_CLOSED = 3

class UserSession:
    def __init__(self, ip: str, port: int, operacion: int, estado: int):
        self.ip = ip                # Dirección IP (str)
        self.port = port            # Puerto (int)
        self.operacion = int(operacion)  # UPLOAD o DOWNLOAD (int, usar 0 o 1)
        self.estado = int(estado)        # CONNECTING, ACTIVE, DISCONNECTING, CONNECTION_CLOSED (int, usar 0-3)
