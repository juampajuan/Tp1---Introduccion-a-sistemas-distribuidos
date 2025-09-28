import socket
import os

from constants import WINDOWS_SIZE, SEQUENCE_NUMBER_RANGE
from packet import Packet

def download_selective_repeat(clientsocket, user_id, server, dest, filename, max_packet_size):
    
    received_total = 0
    current_base = 0
    buffer = {}

    with open(dest, "wb") as f:

        while True:

            data, _ = clientsocket.recvfrom(max_packet_size)
            package = Packet.from_bytes(data)

            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{package.to_string()}"
            )

            received_seq = package.sequenceNumber

            #in seqNumber range (64)
            if (current_base - WINDOWS_SIZE) <= received_seq and received_seq > current_base + WINDOWS_SIZE:

                selective_ack = Packet(
                    user_id, 
                    flags=Packet.FLAG_ACK,
                    sequenceNumber=received_seq,
                    acknowledgmentNumber=received_seq
                )
                clientsocket.sendto(selective_ack.to_bytes(), server)
                print(f"[ACTIVE] ACK de seqNum: {received_seq} fue enviado a {server}.")
                
                #Correctyl received: dentro de la ventana actual
                if current_base <= received_seq and received_seq < current_base + WINDOWS_SIZE:

                    if received_seq not in buffer:

                        buffer[received_seq] = package

                    i = current_base
                    limite = current_base + WINDOWS_SIZE
                    while i < limite:

                        if i in buffer: 

                            payload = (buffer[i]).payload

                            f.write(payload)
                            current_base+=1
                            received_total+= len(payload)
                        
                        else:
                            break
                    
                    if package.fin: 
                        print(f"[ACTIVE] Paquete final de parte de {server} recibido.")
                        print(f"Cantidad total recibida: {received_total}.")
                        break
                    
    return



        
    