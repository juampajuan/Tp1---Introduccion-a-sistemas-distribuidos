import struct
from constants import MAX_PACKET_SIZE, FLAGS_SIZE, USERID_SIZE, PAYLOAD_SIZE

class Packet:
    """
    Estructura del byte de flags (de menor a mayor bit):
    Bit 0: SYN      (0x01)
    Bit 1: ACK      (0x02)
    Bit 2: FIN      (0x04)
    Bit 3: CONNECT  (0x08)
    Bit 4: DATA     (0x10)
    Bits 5-7: Reservados
    """
    FLAG_SYN = 0x01      # Bit 0
    FLAG_ACK = 0x02      # Bit 1
    FLAG_FIN = 0x04      # Bit 2
    FLAG_CONNECT = 0x08  # Bit 3
    FLAG_DATA = 0x10     # Bit 4

    def __init__(self, userId: int, payload: bytes = b'', flags: int = 0):
        self.flags = flags & 0x1F  # Solo 5 bits usados
        self.userId = userId  # unsigned short (2 bytes)
        self.payload = payload.ljust(PAYLOAD_SIZE, b'\x00')  # Rellenar si es necesario

    @property
    def syn(self):
        return (self.flags & self.FLAG_SYN) != 0

    @property
    def ack(self):
        return (self.flags & self.FLAG_ACK) != 0

    @property
    def fin(self):
        return (self.flags & self.FLAG_FIN) != 0

    @property
    def connect(self):
        return (self.flags & self.FLAG_CONNECT) != 0

    @property
    def data(self):
        return (self.flags & self.FLAG_DATA) != 0

    def to_bytes(self) -> bytes:
        return (
            struct.pack('!B', self.flags) +
            struct.pack('!H', self.userId) +
            self.payload
        )

    def toBytes(self) -> bytes:
        return self.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes):
        flags = data[0]
        userId = struct.unpack('!H', data[FLAGS_SIZE:FLAGS_SIZE+USERID_SIZE])[0]
        payload = data[FLAGS_SIZE+USERID_SIZE:FLAGS_SIZE+USERID_SIZE+PAYLOAD_SIZE]
        return cls(userId, payload, flags)

    def to_string(self):
        return (
            f"Packet(flags={self.flags:08b}, syn={int(self.syn)}, ack={int(self.ack)}, fin={int(self.fin)}, "
            f"connect={int(self.connect)}, data={int(self.data)}, userId={self.userId}, payload={self.payload[:20]}...)"
        )
