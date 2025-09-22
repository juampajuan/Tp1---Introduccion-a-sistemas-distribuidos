from constants import MAX_PACKET_SIZE
from packet import Packet
USERID_INICIAL = 65535  # User ID inicial para la handshake


def handshake_with_server(clientsocket,server):
    
    # Arma y envia el paquete inicial con user_id=65535, flags CONNECT|SYN
    try:
        out_packet = Packet(USERID_INICIAL, flags=Packet.FLAG_CONNECT | Packet.FLAG_SYN)
        clientsocket.sendto(out_packet.toBytes, server)

        # Recibo el user_id asignado por el server
        data, _ = clientsocket.recvfrom(MAX_PACKET_SIZE) 
        in_packet = Packet.from_bytes(data)
        user_id = in_packet.userId
        print(f"User ID asignado por el servidor: {user_id}\n")

        ack_packet = Packet(user_id, flags=Packet.FLAG_ACK) 
        clientsocket.sendto(ack_packet.toBytes, server)

        return user_id
    
    except Exception as e:
        print(f"Error durante el handshake con el servidor: {e}")
        exit(1)

