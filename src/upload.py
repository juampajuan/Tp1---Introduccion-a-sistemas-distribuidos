#!/usr/bin/env python3
import argparse
import os
from handshakeWithServer import handshake_with_server 
from socket import *
from constants import MAX_PACKET_SIZE, MAX_PAYLOAD_SIZE
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
    clientsocket.settimeout(TIMEOUT)
    seq = 0            # alternante: 0,1,0,1...
    sent = 0
    try:
        with open(src, "rb") as f:
            while True:
                payload = f.read(MAX_PAYLOAD_SIZE)
                is_last = (payload == b'')
                flags = Packet.FLAG_FIN if is_last else Packet.FLAG_DATA

                packet = Packet(user_id, payload, flags=flags, sequenceNumber=seq)

                retries = 0
                while True:
                    clientsocket.sendto(packet.toBytes(), server)
                    try:
                        data, _ = clientsocket.recvfrom(MAX_PACKET_SIZE)
                        ack = Packet.from_bytes(data)

                        if (ack.userId == user_id
                            and ack.ack
                            and ack.acknowledgmentNumber == seq):
                            break  # ACK correcto para este seq
                    except timeout:
                        pass

                    retries += 1
                    if retries > MAX_RETRIES:
                        print("Número máximo de reintentos alcanzado. Abortando.")
                        return

                if is_last:
                    break

                sent += len(payload)
                seq ^= 1  # alternar 0/1
    finally:
        clientsocket.settimeout(None)
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
