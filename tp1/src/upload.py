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
    p.add_argument("-v","--verbose", action="store_true")
    p.add_argument("-r","--protocol", choices=["sw","sr"], default="sw", help="Protocolo de recuperación de errores (sw=Stop&Wait, sr=SelectiveRepeat)")

    return p.parse_args()

def upload_stop_and_wait(clientsocket, server, src, name, verbose):
      # Envia encabezado simple (texto) con intencion de upload
    # protocolo minimo: "UPLOAD <nombre> <tamaño> \n"

    header = f"UPLOAD {name} {os.path.getsize(src)} \n"

    clientsocket.sendto(header.encode(), server)

    # Envia el archivo en bloques de tamaño CHUNK (sin confiabilidad por ahora)

    sent = 0
    with open(src, "rb") as f:
        while True:
            chunk = f.read(CHUNK)
            if not chunk:
                break
            clientsocket.sendto(chunk, server)
            sent += len(chunk)
            print(f"\rEnviado {sent} bytes", end="", flush=True)

    print("\n")    
     


def main():
    args = parse_args()

    # Valido archivo
    if not os.path.isfile(args.src):
        print("El archivo no existe")
        return

    server = (args.host, args.port)

    # abro socket UDP IPv4
    clientsocket = socket(AF_INET, SOCK_DGRAM)

    if args.protocol == "sw":
            upload_stop_and_wait(clientsocket, server, args.src, args.name, args.verbose)
    elif args.protocol == "sr":
            print("Protocolo Selective Repeat no implementado todavia")
    else:
            print("Protocolo desconocido")
    
    clientsocket.close()
    
    
    

    

if __name__ == "__main__":
    main()
