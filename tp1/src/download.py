from socket import * 
import argparse
import os
from handshakeWithServer import handshake_with_server
from constants import MAX_PACKET_SIZE, PAYLOAD_SIZE
from packet import Packet


TIMEOUT = 2
MAX_RETRIES = 5


def main():
    args = parse_args()

    server = (args.host, args.port)

    with socket(AF_INET, SOCK_DGRAM) as clientsocket:

        user_id = handshake_with_server(clientsocket, server)

        if args.protocol == "dsw" :
            download_stop_and_wait(clientsocket, user_id, server, args.dst, args.name)
        elif  args.protocol == "dsr" :
            #download_selective_repeat(clientsocket, user_id, server, args.src, args.name)
            print("Selective Repeat no implementado.")
        else:
            print("Funcionalidad desconocida.")


def parse_args():
    p = argparse.ArgumentParser(description = "Cliente Download (UDP, version mínima)")
    p.add_argument("-H", "--host", required=True, help= "IP Del servidor")
    p.add_argument("-p", "--port", type=int, required=True, help="Puerto del servidor")
    p.add_argument("-d", "--dst", required=True, help="Ruta del destino local")
    p.add_argument("-n", "--name", required=True, help="Ruta del archivo remoto")
    p.add_argument("-v","--verbose", action="store_true")
    p.add_argument("-r","--protocol", choices=["dsw","dsr"], default="dsw", help="Protocolo de recuperación de errores (dsw=DownloadStop&Wait, dsr=DownloadSelectiveRepeat)")

    return p.parse_args()

def download_stop_and_wait(clientsocket, user_id, server, dest, filename):

    clientsocket.settimeout(TIMEOUT)
    received = 0
    #seq = 0 #Falta implementar seq en Packet

    with open(dest, "wb") as f:

        #Peticion para que server envie file
        #Hay que coordinar el formato de mensaje con el server, dejo un boceto
        file_petition = filename.encode()[:PAYLOAD_SIZE]
        petition = Packet(user_id, file_petition, flags=Packet.FLAG_DATA)
        clientsocket.sendto(petition.to_bytes(), server)
        

        while True:

            try:
                data, _ = clientsocket.recvfrom(MAX_PACKET_SIZE)
                package = Packet.from_bytes(data)

                if package.data:
                    #Hacer algo mas prolijo, deshacerse de los 0 de autorelleno. Un atributo de tamaño real en Packet
                    f.write(package.payload) 
                    received += len(package.payload)

                    #Enviar un ack, podemos usar el seq o el tamaño acumulado para añadir seguridad. Ahora esta vacio
                    ack = Packet(user_id, b'', flags=Packet.FLAG_ACK)
                    clientsocket.sendto(ack.to_bytes(), server)

                if package.fin:
                    print("End of file")
                    break

            except socket.timeout:
                print("Timeout alcanzado. Proceso terminado.")
                return 