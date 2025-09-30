from .constants import PACKET_HEADER_SIZE
from .packet import Packet

TIMEOUT = 2  # Timeout en segundos
MAX_RETRIES = 5  # Timeout en segundos

def upload_stop_and_wait(clientsocket, user_id, server, src, max_payload_size, from_server = False, user_session = None):

    clientsocket.settimeout(TIMEOUT)
    seq = 0            # alternante: 0,1,0,1...
    sent = 0
    try:
        with open(src, "rb") as f:
            while True:
                payload = f.read(max_payload_size)
                is_last = (payload == b'')
                flags = Packet.FLAG_FIN if is_last else Packet.FLAG_DATA
                print(f"Longitud del payload: {len(payload)}")
                # Mostrar el payload con saltos de línea si es texto
                # try:
                #     payload_str = payload.decode('utf-8')
                #     print(f"Payload a enviar:\n{payload_str}\n")
                # except Exception:
                #     print(f"Payload a enviar (binario):\n{payload}\n")
                packet = Packet(user_id, payload, flags=flags, sequence_number=seq)

                retries = 0
                while True:

                    clientsocket.sendto(packet.toBytes(), server)
                    try:   
                        if from_server:
                            ack = user_session.queue.get()
                        else:
                            data, _ = clientsocket.recvfrom(max_payload_size)
                            ack = Packet.from_bytes(data)

                        print(f"Recibi ack {ack.acknowledgment_number}")

                        if (ack.userId == user_id
                            and ack.ack
                            and ack.acknowledgment_number == seq):
                            break  # ACK correcto para este seq
                    except clientsocket.timeout:
                        pass

                    retries += 1
                    if retries > MAX_RETRIES:
                        print("Número máximo de reintentos alcanzado. Abortando.")
                        return

                if is_last:
                    break

                sent += len(payload) + PACKET_HEADER_SIZE
                seq ^= 1  # alternar 0/1
    finally:
        clientsocket.settimeout(None)
    print(f"Archivo enviado correctamente. Total de bytes enviados: {sent}")


def download_stop_and_wait(clientsocket, user_id, addr, dest, max_payload_size, from_server = False, user_session = None):

    seq = 0
    received_total = 0

    with open(dest, "wb") as f:

        while True:

            if from_server:
                package = user_session.queue.get()
            else:
                data, _ = clientsocket.recvfrom(PACKET_HEADER_SIZE+max_payload_size)
                package = Packet.from_bytes(data)


            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{package.to_string()}"
            )

            ack = Packet(
                user_id,
                flags=(Packet.FLAG_ACK),
                sequence_number=package.sequence_number,
                acknowledgment_number=package.sequence_number
                #acknowledgementNumber = package.sequenceNumber
                )
            
            if from_server:
                user_session.sock.sendto(ack.to_bytes(), addr)
            else:
                clientsocket.sendto(ack.to_bytes(), addr)
            
            print(
                f"[ACTIVE] ACK enviado a userId {user_id}: "
                f"{ack.to_string()}")
            
            
            if package.sequence_number == seq:

                payload = package.payload
                print(f"Longitud del payload recibido: {len(payload)}")

                # Mostrar el payload con saltos de línea si es texto
                # try:
                #     payload_str = payload.decode('utf-8')
                #     print(f"Payload recibido:\n{payload_str}\n")
                # except Exception:
                #     print(f"Payload recibido binario:\n{payload}\n")
                f.write(payload)
                received_total+=len(payload)

                seq ^= 1 

            if package.fin:
                print(f"[ACTIVE] Paquete final de parte de {addr} recibido.")
                print(f"Cantidad total recibida: {received_total}.")
                break
