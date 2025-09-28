import socket
import os

from packet import Packet

def download_stop_and_wait(clientsocket, user_id, server, dest, filename, max_packet_size):

    seq = 0
    received_total = 0

    with open(dest, "wb") as f:

        while True:

            data, _ = clientsocket.recvfrom(max_packet_size)
            package = Packet.from_bytes(data)

            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{package.to_string()}"
            )

            ack = Packet(
                user_id,
                flags=(Packet.FLAG_ACK),
                sequenceNumber=seq,
                acknowledgmentNumber=seq
                #acknowledgementNumber = package.sequenceNumber
                )
            clientsocket.sendto(ack.to_bytes(), server)
            print(
                f"[ACTIVE] ACK enviado a userId {user_id}: "
                f"{ack.to_string()}")
            
            if package.sequenceNumber == seq:  
                
                #Añadir rstrip con tamaño de paquete real.

                payload = package.payload
                f.write(payload)
                received_total+=len(payload)

                seq ^= 1 
            
            if package.fin:
                print(f"[ACTIVE] Paquete final de parte de {server} recibido.")
                print(f"Cantidad total recibida: {received_total}.")
                break 