import struct
from constants import MAX_PAYLOAD_SIZE


class Packet:
    """
    Estructura del packet (en bytes):
    ------------------------------------------------------
    | userId (unsigned short)      | 2 bytes            |
    | flags (unsigned char)        | 1 byte             |
    | sequenceNumber (unsigned int)| 4 bytes            |
    | acknowledgmentNumber (unsigned int) | 4 bytes     |
    | payload (bytes)              | MAX_PAYLOAD_SIZE bytes |
    ------------------------------------------------------
    Total header: 11 bytes (sin payload)

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

    def __init__(self, userId: int, payload: bytes = b'', flags: int = 0,
                 sequenceNumber: int = 0, acknowledgmentNumber: int = 0):
        self.userId = userId
        self.flags = flags & 0x1F  # Solo 5 bits usados (1 byte)
        self.sequenceNumber = sequenceNumber
        self.acknowledgmentNumber = acknowledgmentNumber
        self.payload = payload.ljust(MAX_PAYLOAD_SIZE, b'\x00')

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
            struct.pack('!H', self.userId) +
            struct.pack('!B', self.flags) +
            struct.pack('!I', self.sequenceNumber) +
            struct.pack('!I', self.acknowledgmentNumber) +
            self.payload
        )

    def toBytes(self) -> bytes:
        return self.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes):
        userId = struct.unpack('!H', data[0:2])[0]
        flags = data[2]
        sequenceNumber = struct.unpack('!I', data[3:7])[0]
        acknowledgmentNumber = struct.unpack('!I', data[7:11])[0]
        payload = data[11:11+MAX_PAYLOAD_SIZE]
        return cls(userId,
                   payload,
                   flags,
                   sequenceNumber,
                   acknowledgmentNumber)

    def to_string(self):
        return (
            f"Packet(userId={self.userId}, flags={self.flags:08b}, "
            f"syn={int(self.syn)}, ack={int(self.ack)}, fin={int(self.fin)}, "
            f"connect={int(self.connect)}, data={int(self.data)}, "
            f"sequenceNumber={self.sequenceNumber}, "
            f"acknowledgmentNumber={self.acknowledgmentNumber}, "
            f"payload={self.payload[:20]}...)"
        )