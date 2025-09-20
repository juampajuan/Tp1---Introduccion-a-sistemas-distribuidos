#!/usr/bin/env python3
import argparse
from socket import *
import os

CHUNK = 1024 #Mas adelante lo hacemos configurable

def parse_args():
    p = argparse.ArgumentParser(description = "Cliente Upload (UDP, version mínima)")
    p.add_argument("-H", "--host", required=True, help= "IP Del servidor")
    p.add_argument("-p", "--port", type=int, required=True, help="Puerto del servidor")
    p.add_argument("-s", "--src", required=True, help="Ruta del archivo local")
    p.add_argument("-n", "--name", required=True, help="Nombre destino en el servidor")

    return p.parse_args()


def main():
    args = parse_args()

    server = (args.host, args.port)

    # Valido archivo
    if not os.path.isfile(args.src):
        print("El archivo no existe")
        return
    
    # abro socket UDP IPv4
    clientsocket = socket(AF_INET, SOCK_DGRAM)

    # Envia encabezado simple (texto) con intencion de upload
    # protocolo minimo: "UPLOAD <nombre> <tamaño> \n"

    header = f"UPLOAD {args.name} {os.path.getsize(args.src)} \n"

    clientsocket.sendto(header.encode(), server)

    # Envia el archivo en bloques de tamaño CHUNK (sin confiabilidad por ahora)

    sent = 0
    with open(args.src, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            clientsocket.sendto(chunk, server)
            sent += len(chunk)
            print(f"\rEnviado {sent} bytes", end="", flush=True)

    print("\n")    
    clientsocket.close()

if __name__ == "__main__":
    main()
