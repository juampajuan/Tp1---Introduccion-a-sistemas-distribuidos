import socket
import os
import time
import queue
import logging

from .constants import WINDOW_SIZE, SEQUENCE_NUMBER_RANGE, PAYLOAD_SIZE, PACKET_HEADER_SIZE
from .packet import Packet
from .tools import format_time

logger = logging.getLogger("SR")

TIMEOUT = 2 /1000  # Timeout en segundos
MAX_RETRIES = 40 # Número máximo de reintentos para enviar un paquete
RECV_TIMEOUT = 0.01 # para no bloquear en recvfrom
TIMEOUT_RTX = 0.15 # Timeout para retransmisión en Selective Repeat
timeout_server_dsr = 0.2 # Timeout en segundos
timeout_client_upload_sr = 1.2 # Timeout en segundos

def _in_window(seq, base, size, modulo):
    return ((seq - base) % modulo) < size

def _next_seq(x, modulo):
    return (x + 1) % modulo

def upload_selective_repeat(clientsocket, user_id, server, src, max_payload_size, from_server=False, user_session=None):
    if not from_server:
        clientsocket.settimeout(RECV_TIMEOUT)

    window = {}          # seq -> {"pkt": Packet, "sent_at": float, "retries": int, "acked": bool}
    window_base = 0
    next_seq = 0
    sent = 0
    eof = False

    ini = time.perf_counter()

    with open(src, "rb") as f:
        while True:
            # (A) Recibir y procesar ACKs disponibles
            try:
                while True:
                    if from_server:
                        try:
                            ack = user_session.queue.get(timeout=RECV_TIMEOUT)
                        except queue.Empty:
                            break
                    else:
                        try:
                            data, _ = clientsocket.recvfrom(PACKET_HEADER_SIZE + max_payload_size)
                        except socket.timeout:
                            break
                        ack = Packet.from_bytes(data)

                    if ack.connect == 1:
                        # cliente recibe nuevamente el synack porque se perdio
                        # el ultimo ack que envio el cliente para que el server cierre el handshake
                        # reenvio el ultimo ack para que el server cierre el handshake
                        ack = Packet(user_id, flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK)
                        clientsocket.sendto(ack.to_bytes(), server)
                        continue

                    if not ack.ack or ack.userId != user_id:
                        continue

                    ackn = ack.acknowledgment_number

                    # <<< clave: NO filtrar por _in_window en ACKs.
                    # Si el ACK corresponde a un paquete en vuelo, marcarlo.
                    if ackn in window:
                        window[ackn]["acked"] = True

                        # deslizá base modularmente mientras el primer pendiente esté acked
                        while window_base in window and window[window_base]["acked"]:
                            window.pop(window_base)
                            window_base = _next_seq(window_base, SEQUENCE_NUMBER_RANGE)

            except Exception:
                pass  # no bloquear

            # (B) Retransmitir vencidos
            now = time.time()
            for s, e in list(window.items()):
                if now - e["sent_at"] >= TIMEOUT_RTX:
                    if e["retries"] >= MAX_RETRIES:
                        raise TimeoutError(f"seq {s}: agotó reintentos")
                    if from_server:
                        user_session.sock.sendto(e["pkt"].toBytes(), server)
                    else:
                        clientsocket.sendto(e["pkt"].toBytes(), server)
                    e["sent_at"] = time.time()
                    e["retries"] += 1

            # (C) Llenar ventana con nuevos paquetes (acá sí usar _in_window)
            while (not eof) and len(window) < WINDOW_SIZE and _in_window(
                next_seq, window_base, WINDOW_SIZE, SEQUENCE_NUMBER_RANGE
            ):
                payload = f.read(max_payload_size)
                is_last = (payload == b"")
                flags = Packet.FLAG_FIN | Packet.FLAG_DATA if is_last else Packet.FLAG_DATA

                pkt = Packet(user_id, b"" if is_last else payload, flags=flags, sequence_number=next_seq)

                if from_server:
                    user_session.sock.sendto(pkt.toBytes(), server)
                else:
                    clientsocket.sendto(pkt.toBytes(), server)

                window[next_seq] = {"pkt": pkt, "sent_at": time.time(), "retries": 0, "acked": False}

                if not is_last:
                    sent += len(payload)

                eof = is_last
                next_seq = _next_seq(next_seq, SEQUENCE_NUMBER_RANGE)

            # (D) Salir cuando FIN ya fue ACKeado y no quedan en vuelo
            if eof and not window:
                break

    fin = time.perf_counter()
    if not from_server:
        clientsocket.settimeout(None)
    logger.info(f"Archivo enviado correctamente. Total de bytes enviados: {sent}")
    logger.info(f"Tiempo total de transferencia: {format_time(fin - ini)} segundos.")
    return sent


def download_selective_repeat(clientsocket, user_id, server, dest, max_payload_size, from_server=False, user_session=None):
    received_total = 0
    current_base = 0
    buffer = {}
    fin_received = False
    ini = time.perf_counter()
    with open(dest, "wb") as f:
        while True:
            # Recibir siguiente paquete
            if from_server:
                try:
                    package = user_session.queue.get(timeout_server_dsr)
                except queue.Empty:
                    continue
            else:
                data, _ = clientsocket.recvfrom(PACKET_HEADER_SIZE + max_payload_size)
                package = Packet.from_bytes(data)
                if package.connect == 1:
                    # cliente recibe nuevamente el synack porque se perdio
                    # el ultimo ack que envio el cliente para que el server cierre el handshake
                    # reenvio el ultimo ack para que el server cierre el handshake
                    ack = Packet(user_id, flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK)
                    clientsocket.sendto(ack.to_bytes(), server)
                    continue


            # ACK eco del seq recibido (siempre)
            selective_ack = Packet(
                user_id,
                flags=Packet.FLAG_ACK,
                sequence_number=package.sequence_number,
                acknowledgment_number=package.sequence_number
            )
            if from_server:
                user_session.sock.sendto(selective_ack.to_bytes(), server)
            else:
                clientsocket.sendto(selective_ack.to_bytes(), server)

            received_seq = package.sequence_number

            # Aceptar DATA sólo si está en la ventana (con wrap-around correcto)
            if _in_window(received_seq, current_base, WINDOW_SIZE, SEQUENCE_NUMBER_RANGE):

                if received_seq not in buffer:
                    buffer[received_seq] = package

                # drenar en orden empezando desde current_base (modular)
                while current_base in buffer:
                    pkt = buffer.pop(current_base)
                    if pkt.data:
                        f.write(pkt.payload)
                        received_total += len(pkt.payload)
                    current_base = _next_seq(current_base, SEQUENCE_NUMBER_RANGE)

                # si llegó un FIN, marcarlo; salimos cuando buffer queda vacío
                if package.fin:
                    fin_received = True

                if fin_received and len(buffer) == 0:
                    logger.debug(f"[ACTIVE] Paquete final de parte de {server} recibido.")
                    logger.info(f"Cantidad total recibida: {received_total}.")

                    # Quedate un ratito re-ACKeando FINs duplicados
                    FIN_LINGER = 0.8   # 0.5–1.0s va bien
                    end = time.time() + FIN_LINGER
                    while time.time() < end:
                        try:
                            if from_server:
                                dup = user_session.queue.get(timeout=0.1)
                            else:
                                clientsocket.settimeout(0.1)
                                data, _ = clientsocket.recvfrom(PACKET_HEADER_SIZE + max_payload_size)
                                dup = Packet.from_bytes(data)
                        except (queue.Empty, socket.timeout):
                            continue

                        # re-ACK de cualquier duplicado (incluido el FIN)
                        ack = Packet(
                            user_id,
                            flags=Packet.FLAG_ACK,
                            sequence_number=dup.sequence_number,
                            acknowledgment_number=dup.sequence_number
                        )
                        if from_server:
                            user_session.sock.sendto(ack.to_bytes(), server)
                        else:
                            clientsocket.sendto(ack.to_bytes(), server)
                    break

        fin = time.perf_counter()
        logger.info(f"Tiempo total de transferencia: {format_time(fin - ini)}")

            # fuera de ventana: ya ACKeamos arriba; ignorar payload y seguir
