import socket
import os

from constants import WINDOWS_SIZE, SEQUENCE_NUMBER_RANGE
from packet import Packet

def download_selective_repeat(clientsocket, user_id, server, dest, filename, max_packet_size):
    
    received_total = 0
    current_base = 0
    buffer = [] * WINDOWS_SIZE
    with open(dest, "wb") as f:

        while True:

            data, _ = clientsocket.recvfrom(max_packet_size)
            package = Packet.from_bytes(data)

            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{package.to_string()}"
            )

            received_seq = package.sequenceNumber

            #Correctyl received: dentro de la ventana actual
            if current_base <= received_seq and received_seq < current_base + WINDOWS_SIZE:
                
                selective_ack = Packet(
                    user_id, 
                    flags=Packet.FLAG_ACK,
                    sequenceNumber=received_seq,
                    acknowledgmentNumber=received_seq)
    
    return