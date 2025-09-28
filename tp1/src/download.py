from socket import * 
import argparse
from handshakeWithServer import handshake_with_server
from lib.stop_and_wait import download_stop_and_wait
from lib.selective_repeat import download_selective_repeat
from constants import PACKET_HEADER_SIZE
MAX_RETRIES = 5


def main():
    args = parse_args()

    server = (args.host, args.port)

    try:

        with socket(AF_INET, SOCK_DGRAM) as clientsocket:

            user_id, mtu = handshake_with_server(clientsocket, server, args.protocol, args.dst, args.name)

            max_packet_size = mtu - PACKET_HEADER_SIZE - 28 # 28 bytes para cabecera IP/UDP

            if args.protocol == "dsw" :
                download_stop_and_wait(clientsocket, user_id, server, args.dst, args.name, max_packet_size)
            elif  args.protocol == "dsr" :
                download_selective_repeat(clientsocket, user_id, server, args.src, args.name, max_packet_size)
                print("Selective Repeat no implementado.")
            else:
                print("Funcionalidad desconocida.")

    except Exception:
        print("Error detectado en instancia de try: Download.")
        return


def parse_args():
    p = argparse.ArgumentParser(description = "Cliente Download (UDP, version mínima)")
    p.add_argument("-H", "--host", required=True, help= "IP Del servidor")
    p.add_argument("-p", "--port", type=int, required=True, help="Puerto del servidor")
    p.add_argument("-d", "--dst", required=True, help="Ruta del destino local")
    p.add_argument("-n", "--name", required=True, help="Ruta del archivo remoto")
    p.add_argument("-v","--verbose", action="store_true")
    p.add_argument("-r","--protocol", choices=["dsw","dsr"], default="dsw", help="Protocolo de recuperación de errores (dsw=DownloadStop&Wait, dsr=DownloadSelectiveRepeat)")

    return p.parse_args()