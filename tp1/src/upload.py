#!/usr/bin/env python3
import argparse
import os
from handshakeWithServer import handshake_with_server 
from socket import *
from constants import MAX_PACKET_SIZE, PAYLOAD_SIZE
from packet import Packet

#constantes

TIMEOUT = 2  # Timeout en segundos
MAX_RETRIES = 5  # Número máximo de reintentos para enviar un paquete

def parse_args():
    p = argparse.ArgumentParser(description = "Cliente Upload (UDP, version mínima)")
    p.add_argument("-H", "--host", required=True, help= "IP Del servidor")
    p.add_argument("-p", "--port", type=int, required=True, help="Puerto del servidor")
    p.add_argument("-s", "--src", required=True, help="Ruta del archivo local")
    p.add_argument("-n", "--name", required=True, help="Nombre destino en el servidor")
    p.add_argument("-v","--verbose", action="store_true")
    p.add_argument("-r","--protocol", choices=["sw","sr"], default="sw", help="Protocolo de recuperación de errores (sw=Stop&Wait, sr=SelectiveRepeat)")

    return p.parse_args()


def upload_stop_and_wait(clientsocket, user_id, server, src):

    # Envia el archivo en bloques de tamaño PAYLOAD_SIZE
    clientsocket.settimeout(TIMEOUT)  # Timeout de 5 segundos
    seq = 0
    sent = 0

    try:
        with open(src, "rb") as f:
            while True:
                # Armo y envio el paquete con el user_id y data
                payload = f.read(PAYLOAD_SIZE)
                is_last = (payload == b'')
                packet_flag = Packet.FLAG_FIN if is_last else Packet.FLAG_DATA
                packet = Packet(user_id, payload, flags = packet_flag) #Falta agregar numero de seq

                retries = 0

                while True:
                    clientsocket.recvfrom(packet.toBytes,server) 
                    try:
                        data, _ = clientsocket.recvfrom(MAX_PACKET_SIZE)
                        ack_packet = Packet.from_bytes(data)

                        if(ack_packet.ack and ack_packet.userId == user_id):
                            break  # ACK válido recibido, salir del bucle de reintentos 
                    except socket.timeout:
                        pass

                    retries += 1

                    if retries > MAX_RETRIES:
                        print("Número máximo de reintentos alcanzado. Abortando.")
                        return

                if is_last:
                    break  # Archivo completamente enviado
                
                sent += len(payload)

                
                seq ^= 1  # Alterna el número de secuencia entre 0 y 1

    finally:
        clientsocket.settimeout(None)  # Desactivo el timeout
    print(f"Archivo enviado correctamente. Total de bytes enviados: {sent}")
     


def main():
    args = parse_args()

    # Valido archivo
    if not os.path.isfile(args.src):
        print("El archivo no existe")
        return

    server = (args.host, args.port)

    with socket(AF_INET, SOCK_DGRAM) as clientsocket:

        user_id = handshake_with_server(clientsocket, server)

        protocolos = { "sw": upload_stop_and_wait, "sr": lambda *a: print("Protocolo Selective Repeat no implementado todavia") }

        if args.protocol in protocolos:
            protocolos[args.protocol](clientsocket, user_id, server, args.src)
        else:
                print("Protocolo desconocido")
    


if __name__ == "__main__":
    main()
