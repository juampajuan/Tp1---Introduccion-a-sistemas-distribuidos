import struct


class Packet:
    """
    Estructura del packet (en bytes):
    ------------------------------------------------------
    | userId (unsigned short)      | 2 bytes            |
    | flags (unsigned char)        | 1 byte             |
    | sequenceNumber (unsigned int)| 4 bytes            |
    | acknowledgmentNumber (unsigned int) | 4 bytes     |
    | payloadLength (unsigned short)      | 2 bytes     |
    | payload (bytes)              | variable           |
    ------------------------------------------------------
    Total header: 13 bytes (sin payload)

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

    def __init__(self, user_id: int, payload: bytes = b'', flags: int = 0,
                 sequence_number: int = 0, acknowledgment_number: int = 0):
        self.userId = user_id
        self.flags = flags & 0x1F  # Solo 5 bits usados (1 byte)
        self.sequence_number = sequence_number
        self.acknowledgment_number = acknowledgment_number
        self.payload_length = len(payload)
        # Inicialmente vacío, puede crecer dinámicamente
        self.payload = payload

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
        payload_length = len(self.payload)
        return (
            struct.pack('!H', self.userId) +
            struct.pack('!B', self.flags) +
            struct.pack('!I', self.sequence_number) +
            struct.pack('!I', self.acknowledgment_number) +
            struct.pack('!H', payload_length) +
            self.payload
        )

    def toBytes(self) -> bytes:
        return self.to_bytes()

    @classmethod
    def from_bytes(cls, data: bytes):
        user_id = struct.unpack('!H', data[0:2])[0]
        flags = data[2]
        sequence_number = struct.unpack('!I', data[3:7])[0]
        acknowledgment_number = struct.unpack('!I', data[7:11])[0]
        payload_length = struct.unpack('!H', data[11:13])[0]
        payload = data[13:13 + payload_length]
        return cls(user_id,
                   payload,
                   flags,
                   sequence_number,
                   acknowledgment_number)

    def to_string(self):
        return (
            f"Packet(userId={self.userId}, flags={self.flags:08b}, "
            f"syn={int(self.syn)}, ack={int(self.ack)}, fin={int(self.fin)}, "
            f"connect={int(self.connect)}, data={int(self.data)}, "
            f"sequenceNumber={self.sequence_number}, "
            f"acknowledgmentNumber={self.acknowledgment_number}, "
            f"payloadLength={len(self.payload)},"
            f" payload={self.payload[:20]}...)"
        )
