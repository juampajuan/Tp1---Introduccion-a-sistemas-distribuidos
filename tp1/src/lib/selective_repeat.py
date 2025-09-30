import socket
import os
import time

from .constants import WINDOW_SIZE, SEQUENCE_NUMBER_RANGE, PAYLOAD_SIZE, PACKET_HEADER_SIZE
from .packet import Packet

TIMEOUT = 2 /1000  # Timeout en segundos
MAX_RETRIES = 5  # Número máximo de reintentos para enviar un paquete
RECV_TIMEOUT = 0.01 # para no bloquear en recvfrom
TIMEOUT_RTX = 0.8 # Timeout para retransmisión en Selective Repeat

def _in_window(seq, base, size, modulo):
    return ((seq - base) % modulo) < size

def _next_seq(x, modulo):
    return (x + 1) % modulo

def upload_selective_repeat(clientsocket, user_id, server, src, max_payload_size, from_server = False, user_session = None):
    # 1) poll cortito para no bloquear (no es el timeout de retransmisión)
    if not from_server:
        clientsocket.settimeout(RECV_TIMEOUT)

    print("Empieza uplaod server")
    window = {}          # seq -> {"pkt": Packet, "sent_at": float, "retries": int}
    window_base = 0
    next_seq = 0
    sent = 0
    eof = False

    with open(src, "rb") as f:

        print("Abre el archivo src")
        i = 0
        while True:
            print(f"Iteracion del while mayor no: {i}")

            # --- (A) Recibir todos los ACKs disponibles ---
            try:
                print("Entra al try")
                j = 0
                while True:
                    print(f"Iteracion del while dentro del try para recibir acks nro: {j}")
                    if from_server:
                        if not user_session.queue.empty():
                            print("Cola no vacia")
                            ack = user_session.queue.get()
                        else:
                            break
                    else:
                        data, _ = clientsocket.recvfrom(max_payload_size)
                        ack = Packet.from_bytes(data)
                    print("Recuperamos ack")
                    if not ack.ack: 
                        continue
                    if ack.userId != user_id:
                        continue

                    ackn = ack.acknowledgment_number
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
                    if from_server:
                        user_session.sock.sendto(e["pkt"].toBytes(), server)
                    else:
                        clientsocket.sendto(e["pkt"].toBytes(), server)
                    e["sent_at"] = time.time()
                    e["retries"] += 1

            # --- (C) Llenar ventana con nuevos paquetes ---
            while (not eof) and len(window) < WINDOW_SIZE and _in_window(
                next_seq, window_base, WINDOW_SIZE, SEQUENCE_NUMBER_RANGE
            ):
                payload = f.read(PAYLOAD_SIZE)
                is_last = (payload == b"")
                flags = Packet.FLAG_FIN if is_last else Packet.FLAG_DATA

                pkt = Packet(user_id, b"" if is_last else payload,
                             flags=flags, sequence_number=next_seq)

                if from_server:
                    user_session.sock.sendto(pkt.toBytes(), server)
                else:
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

def download_selective_repeat(clientsocket, user_id, server, dest, max_payload_size, from_server = False, user_session = None):
    
    received_total = 0
    current_base = 0
    buffer = {}
    fin_received = False

    with open(dest, "wb") as f:

        while True:
            if from_server:
                package = user_session.queue.get(TIMEOUT)
            else:
                data, _ = clientsocket.recvfrom(PACKET_HEADER_SIZE+max_payload_size)
                package = Packet.from_bytes(data)

            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{package.to_string()}"
            )

            received_seq = package.sequence_number

            #in seqNumber range (64)
            if (current_base - WINDOW_SIZE) <= received_seq and received_seq < (current_base + WINDOW_SIZE):

                selective_ack = Packet(
                    user_id, 
                    flags=Packet.FLAG_ACK,
                    sequence_number=received_seq,
                    acknowledgment_number=received_seq
                )

                if from_server:
                    user_session.sock.sendto(selective_ack.to_bytes(), server)
                else:
                    clientsocket.sendto(selective_ack.to_bytes(), server)
                print(f"[ACTIVE] ACK de seqNum: {received_seq} fue enviado a {server}.")
                
                #Correctyl received: dentro de la ventana actual
                if current_base <= received_seq and received_seq < current_base + WINDOW_SIZE:

                    if received_seq not in buffer:
                        print(f"[BUFFER_UPDATE] Paquete de nro de secuencia: {received_seq} almacenado")
                        buffer[received_seq] = package

                    i = current_base
                    limite = current_base + WINDOW_SIZE
                    while i < limite:

                        if i in buffer: 

                            payload = (buffer[i]).payload
                            print(f"[BUFFER_UPDATE] Paquete de nro de secuencia: {received_seq} removido de buffer")
                            buffer.pop(i) #Borro entrada para mantener buffer pequeño

                            #Añadir logica rstrip
                            f.write(payload)
                            current_base+=1
                            received_total+= len(payload)
                        
                        else:
                            break

                    if package.fin:
                        fin_received = True
                    
                    if len(buffer) == 0 and fin_received: 
                        print(f"[ACTIVE] Paquete final de parte de {server} recibido.")
                        print(f"Cantidad total recibida: {received_total}.")
                        break
                    
    return



        
    