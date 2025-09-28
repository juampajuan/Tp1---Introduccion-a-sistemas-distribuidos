#!/usr/bin/env python3
import argparse
import os
from handshakeWithServer import handshake_with_server 
from socket import *
from constants import MAX_PAYLOAD_SIZE, WINDOW_SIZE, SEQUENCE_NUMBER_RANGE
from packet import Packet

#constantes
TIMEOUT = 2  # Timeout en segundos
MAX_RETRIES = 5  # Número máximo de reintentos para enviar un paquete
RECV_TIMEOUT = 0.01 # para no bloquear en recvfrom
TIMEOUT_RTX = 2.0 # Timeout para retransmisión en Selective Repeat

def parse_args():
    p = argparse.ArgumentParser(description = "Cliente Upload (UDP, version mínima)")
    p.add_argument("-H", "--host", required=True, help= "IP Del servidor")
    p.add_argument("-p", "--port", type=int, required=True, help="Puerto del servidor")
    p.add_argument("-s", "--src", required=True, help="Ruta del archivo local")
    p.add_argument("-n", "--name", required=True, help="Nombre destino en el servidor")
    p.add_argument("-v","--verbose", action="store_true")
    p.add_argument("-r","--protocol", choices=["sw","sr"], default="sw", help="Protocolo de recuperación de errores (sw=Stop&Wait, sr=SelectiveRepeat)")

    return p.parse_args()
    


def upload_selective_repeat(clientsocket, user_id, server, src):
    """
    Server ACKea el MISMO seq recibido.
    Enviamos solo paquetes nuevos; retransmitimos por timeout por PAQUETE.
    """
    import time
    clientsocket.settimeout(RECV_TIMEOUT)

    base = 0                    # primer seq pendiente (frente de ventana)
    next_seq = 0                # próximo seq libre
    window = {}                    # seq -> {"pkt": Packet, "last": float, "retries": int, "is_fin": bool}
    fin_en_ventana = False      # ya pusimos FIN en la ventana

    def in_window(s):
        # ¿s está dentro de [base, base+W) en aritmética mod N?
        return ((s - base) % SEQUENCE_NUMBER_RANGE) < WINDOW_SIZE

    with open(src, "rb") as f:
        while True:
            # 1) Llenar ventana sólo con NUEVOS paquetes (sin re-enviar todo)
            while not fin_en_ventana and in_window(next_seq):
                payload = f.read(PAYLOAD_SIZE)
                is_last = (payload == b'')
                flags = Packet.FLAG_FIN if is_last else Packet.FLAG_DATA
                package = Packet(
                    userId=user_id,
                    payload=(b'' if is_last else payload),
                    flags=flags,
                    sequenceNumber=next_seq,
                    acknowledgmentNumber=0
                )
                # Envío inicial del nuevo paquete y registro timer
                clientsocket.sendto(package.toBytes(), server)
                window[next_seq] = {
                    "pkt": package,
                    "last": time.time(),
                    "retries": 0,
                    "is_fin": is_last,
                }
                fin_en_ventana = is_last
                next_seq = (next_seq + 1) % SEQUENCE_NUMBER_RANGE

            # 2) Procesar ACK (no bloqueante). ACK == seq recibido
            try:
                data, _ = clientsocket.recvfrom(MAX_PACKET_SIZE)
                ack = Packet.from_bytes(data)
                if ack.userId == user_id and ack.ack:
                    s = ack.acknowledgmentNumber
                    if s in window:
                        del window[s]
                        # Deslizo base todo lo posible
                        while base not in window and base != next_seq:
                            base = (base + 1) % SEQUENCE_NUMBER_RANGE
            except timeout:
                pass  # no llegó ACK ahora

            # 3) Retransmisión selectiva por paquete (si venció su timer)
            now = time.time()
            for s, meta in list(win.items()):
                if now - meta["last"] >= TIMEOUT_RTX:
                    if meta["retries"] >= MAX_RETRIES:
                        print("SR: demasiados reintentos; abortando.")
                        clientsocket.settimeout(None)
                        return
                    clientsocket.sendto(meta["pkt"].toBytes(), server)
                    meta["last"] = now
                    meta["retries"] += 1

            # 4) Salida: FIN ya encolado y todo ACKeado
            if fin_en_ventana and not window:
                break

    clientsocket.settimeout(None)
    print("SR: envío completo con timers por paquete.")



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
