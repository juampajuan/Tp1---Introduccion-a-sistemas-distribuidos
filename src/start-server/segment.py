import struct
from user_session import OP_UPLOAD, OP_DOWNLOAD

# Definición de flags (cada uno puede ser 0 o 1, empaquetados en 3 bits)
FLAG_SYN = 0
FLAG_ACK = 1
FLAG_FIN = 2

class Segment:
    """
    Representa un segmento de datos enviado/recibido por el socket.
    userId: int (2 bytes)
    operacion: int (1 byte, OP_UPLOAD o OP_DOWNLOAD)
    flags: int (1 byte, 3 bits: SYN, ACK, FIN empaquetados)
    payload: bytes (resto del paquete)
    """
    HEADER_FORMAT = 'HBB'  # userId (2 bytes), operacion (1 byte, int), flags (1 byte)
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    MAX_PACKET_SIZE = 400
    MAX_PAYLOAD_SIZE = MAX_PACKET_SIZE - HEADER_SIZE

    def __init__(self, userId, operacion, syn=0, ack=0, fin=0, payload=b''):
        self.userId = userId
        self.operacion = int(operacion)  # int, OP_UPLOAD o OP_DOWNLOAD
        # Empaquetar los flags en 3 bits: SYN (bit 0), ACK (bit 1), FIN (bit 2)
        self.flags = ((bool(syn) & 0x1) << 0) | ((bool(ack) & 0x1) << 1) | ((bool(fin) & 0x1) << 2)
        self.payload = payload           # bytes

    def to_bytes(self):
        header = struct.pack(self.HEADER_FORMAT, self.userId, self.operacion & 0xFF, self.flags & 0b111)
        return header + self.payload

    @classmethod
    def from_bytes(cls, data):
        if len(data) < cls.HEADER_SIZE:
            raise ValueError('Paquete demasiado pequeño para un segmento válido')
        userId, operacion, flags = struct.unpack(cls.HEADER_FORMAT, data[:cls.HEADER_SIZE])
        payload = data[cls.HEADER_SIZE:]
        # Desempaquetar los flags
        syn = (flags >> 0) & 0x1
        ack = (flags >> 1) & 0x1
        fin = (flags >> 2) & 0x1
        return cls(userId, operacion, syn, ack, fin, payload)

    def get_flag(self, flag):
        """Devuelve el valor (0 o 1) del flag solicitado (FLAG_SYN, FLAG_ACK, FLAG_FIN)"""
        return (self.flags >> flag) & 0x1

    def set_flag(self, flag, value):
        """Setea el valor (0 o 1) del flag solicitado (FLAG_SYN, FLAG_ACK, FLAG_FIN)"""
        if value:
            self.flags |= (1 << flag)
        else:
            self.flags &= ~(1 << flag)
