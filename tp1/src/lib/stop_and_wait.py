from .constants import PACKET_HEADER_SIZE
from .packet import Packet
from .tools import format_time
import socket
import time
import queue
import logging
TIMEOUT = 2 / 1000  # Timeout en segundos
MAX_RETRIES = 30  # Timeout en segundos
timeout_server_dsw = 0.05  # Timeout en segundos
timeout_client_upload_sw = 0.05  # Timeout en segundos

logger = logging.getLogger("SW")


def upload_stop_and_wait(
        clientsocket,
        user_id,
        server,
        src,
        max_payload_size,
        from_server=False,
        user_session=None):

    clientsocket.settimeout(timeout_client_upload_sw)
    seq = 0            # alternante: 0,1,0,1...
    sent = 0
    try:
        ini = time.perf_counter()
        with open(src, "rb") as f:
            while True:
                payload = f.read(max_payload_size)
                is_last = (payload == b'')
                flags = (
                    Packet.FLAG_FIN | Packet.FLAG_DATA
                    if is_last else Packet.FLAG_DATA
                )

                packet = Packet(
                    user_id,
                    payload,
                    flags=flags,
                    sequence_number=seq)

                retries = 0
                while True:

                    clientsocket.sendto(packet.toBytes(), server)
                    try:
                        if from_server:
                            ack = user_session.queue.get(
                                timeout=timeout_client_upload_sw)
                        else:
                            data, _ = clientsocket.recvfrom(max_payload_size)
                            ack = Packet.from_bytes(data)
                            if ack.connect == 1:
                                # cliente recibe nuevamente el synack
                                # porque se perdio el ultimo ack que envio
                                # el cliente para que el server cierre
                                # el handshake reenvio el ultimo ack para
                                # que el server cierre el handshake
                                val = Packet.FLAG_CONNECT | Packet.FLAG_ACK
                                ack = Packet(
                                    user_id,
                                    flags=val)
                                clientsocket.sendto(ack.to_bytes(), server)
                                continue

                        if (ack.userId == user_id
                            and ack.ack
                                and ack.acknowledgment_number == seq):
                            break  # ACK correcto para este seq
                    except (socket.timeout, queue.Empty):
                        pass

                    retries += 1
                    if retries > MAX_RETRIES:
                        logger.error(
                            "Número máximo de reintentos alcanzado. "
                            "Abortando.")
                        return

                if is_last:
                    sent += len(payload) + PACKET_HEADER_SIZE
                    break

                sent += len(payload) + PACKET_HEADER_SIZE
                seq ^= 1  # alternar 0/1
    finally:
        clientsocket.settimeout(None)
        fin = time.perf_counter()
    logger.info(
        f"Archivo enviado correctamente. Total de bytes enviados: {sent}")
    logger.info(f"Tiempo total de transferencia: {format_time(fin - ini)}")


def download_stop_and_wait(
    clientsocket,
    user_id,
    addr,
    dest,
    max_payload_size,
    from_server=False,
    user_session=None,
):
    seq = 0
    received_total = 0

    with open(dest, "wb") as f:
        ini = time.perf_counter()
        while True:
            # Recibir paquete (cola si corre en el server)
            if from_server:
                try:
                    package = user_session.queue.get(
                        timeout=timeout_server_dsw)
                except queue.Empty:
                    # No llegó a tiempo (delay/pérdida); seguir esperando
                    continue
            else:
                data, _ = clientsocket.recvfrom(
                    PACKET_HEADER_SIZE + max_payload_size)
                package = Packet.from_bytes(data)
                if package.connect == 1:
                    # cliente recibe nuevamente el synack porque se perdio
                    # el ultimo ack que envio el cliente para que
                    # el server cierre el handshake reenvio el ultimo ack
                    # que el server cierre el handshake
                    ack = Packet(
                        user_id, flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK)
                    clientsocket.sendto(ack.to_bytes(), addr)
                    continue

            # Enviar ACK eco del seq recibido (siempre ACKear)
            ack = Packet(
                user_id,
                flags=Packet.FLAG_ACK,
                sequence_number=package.sequence_number,
                acknowledgment_number=package.sequence_number
            )
            if from_server:
                user_session.sock.sendto(ack.to_bytes(), addr)
            else:
                clientsocket.sendto(ack.to_bytes(), addr)

            # Consumir DATA sólo si es el seq esperado; luego alternar
            if package.data and package.sequence_number == seq:
                payload = package.payload
                # print(f"Longitud del payload recibido: {len(payload)}")
                f.write(payload)
                received_total += len(payload) + PACKET_HEADER_SIZE
                seq ^= 1

            # FIN: cerrar cuando llega el FIN (el emisor reintentará hasta que
            # vea este ACK)
            if package.fin:
                fin = time.perf_counter()
                logger.debug(
                    f"[ACTIVE] Paquete final de parte de {addr} recibido.")
                logger.info(f"Cantidad total recibida: {received_total}.")
                logger.info(
                    f"Tiempo total de transferencia: {
                        format_time(
                            fin - ini)} ")
                break
