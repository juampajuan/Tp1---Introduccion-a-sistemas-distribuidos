from constants import MAX_PAYLOAD_SIZE

from packet import Packet
USERID_INICIAL = 65535  # User ID inicial para la handshake


def handshake_with_server(clientsocket, server):
    try:
        # 1) SYN del cliente con seq=0
        syn = Packet(
            USERID_INICIAL,
            flags=Packet.FLAG_CONNECT | Packet.FLAG_SYN,
            sequenceNumber=0,
            acknowledgmentNumber=0
        )
        clientsocket.sendto(syn.toBytes(), server)

        # 2) SYN|ACK del server
        data, _ = clientsocket.recvfrom(MAX_PAYLOAD_SIZE)
        synack = Packet.from_bytes(data)
        user_id = synack.userId
        print(f"User ID asignado por el servidor: {user_id}")

        # 3) ACK final del cliente:
        #    seq_cliente = 1 (siguiente al SYN=0)
        #    ack_cliente = synack.sequenceNumber + 1
        ack = Packet(
            user_id,
            flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK,
            sequenceNumber=1,
            acknowledgmentNumber=synack.sequenceNumber + 1
        )
        clientsocket.sendto(ack.toBytes(), server)
        return user_id

    except Exception as e:
        print(f"Error durante el handshake con el servidor: {e}")
        exit(1)

