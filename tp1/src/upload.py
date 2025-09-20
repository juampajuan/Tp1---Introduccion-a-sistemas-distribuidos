#!/usr/bin/env python3
import argparse
import struct
from socket import *
import os

CHUNK = 1024 #Mas adelante lo hacemos configurable
OPERATION = b'U'
USERID_INICIAL = 0xFFFF

def parse_args():
    p = argparse.ArgumentParser(description = "Cliente Upload (UDP, version mínima)")
    p.add_argument("-H", "--host", required=True, help= "IP Del servidor")
    p.add_argument("-p", "--port", type=int, required=True, help="Puerto del servidor")
    p.add_argument("-s", "--src", required=True, help="Ruta del archivo local")
    p.add_argument("-n", "--name", required=True, help="Nombre destino en el servidor")
    p.add_argument("-v","--verbose", action="store_true")
    p.add_argument("-r","--protocol", choices=["sw","sr"], default="sw", help="Protocolo de recuperación de errores (sw=Stop&Wait, sr=SelectiveRepeat)")

    return p.parse_args()


def handshake(clientsocket,server, src, name):
    
    # Arma y envia el paquete inicial con la operación y el user_id inicial hacia el server.

    payload = f"UPLOAD {name} {os.path.getsize(src)} \n".encode()
    paquete = struct.pack("!H1s", USERID_INICIAL, OPERATION) + payload
    clientsocket.sendto(paquete, server)

    # Recibo el user_id asignado por el server
    data, addr = clientsocket.recvfrom(2)
    user_id, = struct.unpack("!H", data)
    print(f"User ID asignado por el servidor: {user_id}\n")
    return user_id



def upload_stop_and_wait(clientsocket, user_id, server, src, name):

    # Envia el archivo en bloques de tamaño CHUNK (sin confiabilidad por ahora)

    sent = 0
    with open(src, "rb") as f:
        while True:
            payload = f.read(CHUNK)
            if not payload:
                break

            # Armo y envio el paquete con el user_id, operación y payload
            paquete = struct.pack("!H1s", user_id, OPERATION) + payload
            clientsocket.sendto(paquete, server)
            
            sent += len(payload)
            
    print(f"\rEnviado {sent} bytes\n")  
     


def main():
    args = parse_args()

    # Valido archivo
    if not os.path.isfile(args.src):
        print("El archivo no existe")
        return

    server = (args.host, args.port)

    # abro socket UDP IPv4
    clientsocket = socket(AF_INET, SOCK_DGRAM)

    user_id = handshake(clientsocket, server, args.src, args.name)

    if args.protocol == "sw":
            upload_stop_and_wait(clientsocket, user_id, server, args.src, args.name)
    elif args.protocol == "sr":
            print("Protocolo Selective Repeat no implementado todavia")
    else:
            print("Protocolo desconocido")
    
    clientsocket.close()
    


if __name__ == "__main__":
    main()
