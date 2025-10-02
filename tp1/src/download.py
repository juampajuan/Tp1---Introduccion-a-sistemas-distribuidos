from socket import * 
import argparse
from handshakeWithServer import handshake_with_server
from lib.stop_and_wait import download_stop_and_wait
from lib.selective_repeat import download_selective_repeat
from lib.constants import PACKET_HEADER_SIZE, PAYLOAD_SIZE

import logging
logger = logging.getLogger("[DOWNLOAD]")

def parse_args():
    p = argparse.ArgumentParser(description = "Cliente Download (UDP, version mínima)")
    p.add_argument("-H", "--host", required=True, help= "IP Del servidor")
    p.add_argument("-p", "--port", type=int, required=True, help="Puerto del servidor")
    p.add_argument("-d", "--dst", required=True, help="Ruta del destino local")
    p.add_argument("-n", "--name", required=True, help="Nombre del archivo remoto")
    p.add_argument("-v","--verbose", action="store_true")
    p.add_argument("-r","--protocol", choices=["sw","sr"], default="sw", help="Protocolo de recuperación de errores (sw=DownloadStop&Wait, sr=DownloadSelectiveRepeat)")

    return p.parse_args()

def main():
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='[%(levelname)s] %(message)s')
    args = parse_args()

    server = (args.host, args.port)
    filename_with_path = args.dst + args.name
    try:

        with socket(AF_INET, SOCK_DGRAM) as clientsocket:

            user_id = handshake_with_server(clientsocket, server, "d" + args.protocol, args.name)

            max_packet_size = PAYLOAD_SIZE

            if args.protocol == "sw" :
                download_stop_and_wait(clientsocket, user_id, server, filename_with_path, max_packet_size)
            elif  args.protocol == "sr" :
                download_selective_repeat(clientsocket, user_id, server, filename_with_path, max_packet_size)
            else:
                logger.error("Funcionalidad desconocida.")

    except Exception as e:
        logger.error(f"Error detectado en instancia de try: Download. {e}")
        return

if __name__ == "__main__":
    main()