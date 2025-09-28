import socket
import time
from constants import MAX_PAYLOAD_SIZE, WINDOW_SIZE, SEQUENCE_NUMBER_RANGE
from packet import Packet

MAX_RETRIES = 5  # Número máximo de reintentos para enviar un paquete
RECV_TIMEOUT = 0.01 # para no bloquear en recvfrom
TIMEOUT_RTX = 0.8 # Timeout para retransmisión en Selective Repeat


def _in_window(seq, base, size, modulo):
    return ((seq - base) % modulo) < size

def _next_seq(x, modulo):
    return (x + 1) % modulo

def upload_selective_repeat(clientsocket, user_id, server, src,max_packet_size):
    # 1) poll cortito para no bloquear (no es el timeout de retransmisión)
    clientsocket.settimeout(RECV_TIMEOUT)

    window = {}          # seq -> {"pkt": Packet, "sent_at": float, "retries": int}
    window_base = 0
    next_seq = 0
    sent = 0
    eof = False

    with open(src, "rb") as f:
        while True:
            # --- (A) Recibir todos los ACKs disponibles ---
            try:
                while True:
                    data, _ = clientsocket.recvfrom(max_packet_size)
                    ack = Packet.from_bytes(data)

                    if not ack.ack: 
                        continue
                    if ack.userId != user_id:
                        continue

                    ackn = ack.acknowledgmentNumber
                    if ackn in window:
                        del window[ackn]
                        # deslizar base tanto como se pueda
                        while (window_base not in window) and (window_base != next_seq):
                            window_base = _next_seq(window_base, SEQUENCE_NUMBER_RANGE)

            except socket.timeout:
                pass  # no había ACKs ahora

            # --- (B) Retransmitir paquetes vencidos ---
            now = time.time()
            for s, e in list(window.items()):
                if now - e["sent_at"] >= TIMEOUT_RTX:
                    if e["retries"] >= MAX_RETRIES:
                        raise TimeoutError(f"seq {s}: agotó reintentos")
                    clientsocket.sendto(e["pkt"].toBytes(), server)
                    e["sent_at"] = time.time()
                    e["retries"] += 1

            # --- (C) Llenar ventana con nuevos paquetes ---
            while (not eof) and len(window) < WINDOW_SIZE and _in_window(
                next_seq, window_base, WINDOW_SIZE, SEQUENCE_NUMBER_RANGE
            ):
                payload = f.read(MAX_PAYLOAD_SIZE)
                is_last = (payload == b"")
                flags = Packet.FLAG_FIN if is_last else Packet.FLAG_DATA

                pkt = Packet(user_id, b"" if is_last else payload,
                             flags=flags, sequenceNumber=next_seq)

                clientsocket.sendto(pkt.toBytes(), server)
                window[next_seq] = {"pkt": pkt, "sent_at": time.time(), "retries": 0}

                if is_last:
                    eof = True
                else:
                    sent += len(payload)

                next_seq = _next_seq(next_seq, SEQUENCE_NUMBER_RANGE)

            # --- (D) Condición de salida ---
            if eof and not window:
                break

            # pequeño descanso opcional (el poll del socket ya frena la CPU)
            # time.sleep(0.001)

    clientsocket.settimeout(None)
    print(f"Archivo enviado correctamente. Total de bytes enviados: {sent}")
    return sent
        