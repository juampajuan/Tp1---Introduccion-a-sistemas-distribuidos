#!/usr/bin/env python3
import argparse
import os
import logging
from lib.handshakeWithServer import handshake_with_server
from lib.selective_repeat import upload_selective_repeat
from lib.stop_and_wait import upload_stop_and_wait
from socket import *
from lib.constants import PAYLOAD_SIZE
from lib.packet import Packet

# Logger específico para este módulo
logger = logging.getLogger("[UPLOAD]")

# constantes
TIMEOUT = 2  # Timeout en segundos
MAX_RETRIES = 5  # Número máximo de reintentos para enviar un paquete
RECV_TIMEOUT = 0.01  # para no bloquear en recvfrom
TIMEOUT_RTX = 0.8  # Timeout para retransmisión en Selective Repeat


def parse_args():
    p = argparse.ArgumentParser(
        description="Cliente Upload (UDP, version mínima)")

    p.add_argument("-H", "--host", required=True, help="IP Del servidor")
    p.add_argument(
        "-p",
        "--port",
        type=int,
        required=True,
        help="Puerto del servidor")
    p.add_argument("-s", "--src", required=True, help="Ruta del archivo local")
    p.add_argument(
        "-n",
        "--name",
        required=True,
        help="Nombre destino en el servidor")
    p.add_argument("-v", "--verbose", action="store_true")
    p.add_argument(
        "-r",
        "--protocol",
        choices=[
            "sw",
            "sr"],
        default="sw",
        help="Protocolo de recuperación de errores (sw=Stop&Wait, sr=SelectiveRepeat)")

    return p.parse_args()


def main():
    args = parse_args()

    # Configuración del logger global
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='[%(levelname)s] %(message)s')

    filenameWithPath = args.src + args.name

    # Valido archivo
    if not os.path.isfile(filenameWithPath):
        logger.error("El archivo no existe")
        return

    server = (args.host, args.port)

    with socket(AF_INET, SOCK_DGRAM) as clientsocket:

        user_id = handshake_with_server(
            clientsocket, server, args.protocol, args.name)

        max_payload_size = PAYLOAD_SIZE  # pasar a una constante

        protocolos = {
            "sw": upload_stop_and_wait,
            "sr": upload_selective_repeat}

        if args.protocol in protocolos:
            protocolos[args.protocol](
                clientsocket, user_id, server, filenameWithPath, max_payload_size)
        else:
            logger.error("Protocolo desconocido")


if __name__ == "__main__":
    main()
