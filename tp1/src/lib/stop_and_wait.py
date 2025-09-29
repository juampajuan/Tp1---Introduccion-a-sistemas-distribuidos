from ..packet import Packet

TIMEOUT = 2  # Timeout en segundos
MAX_RETRIES = 5  # Timeout en segundos

def upload_stop_and_wait(clientsocket, user_id, server, src, max_packet_size):
    clientsocket.settimeout(TIMEOUT)
    seq = 0            # alternante: 0,1,0,1...
    sent = 0
    try:
        with open(src, "rb") as f:
            while True:
                payload = f.read(max_packet_size)
                is_last = (payload == b'')
                flags = Packet.FLAG_FIN if is_last else Packet.FLAG_DATA

                packet = Packet(user_id, payload, flags=flags, sequenceNumber=seq)

                retries = 0
                while True:
                    clientsocket.sendto(packet.toBytes(), server)
                    try:
                        data, _ = clientsocket.recvfrom(max_packet_size)
                        ack = Packet.from_bytes(data)

                        if (ack.userId == user_id
                            and ack.ack
                            and ack.acknowledgmentNumber == seq):
                            break  # ACK correcto para este seq
                    except clientsocket.timeout:
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


def download_stop_and_wait(clientsocket, user_id, server, dest, max_packet_size):

    seq = 0
    received_total = 0

    with open(dest, "wb") as f:

        while True:

            data, _ = clientsocket.recvfrom(max_packet_size)
            package = Packet.from_bytes(data)

            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{package.to_string()}"
            )

            ack = Packet(
                user_id,
                flags=(Packet.FLAG_ACK),
                sequenceNumber=package.sequenceNumber,
                acknowledgmentNumber=package.sequenceNumber
                #acknowledgementNumber = package.sequenceNumber
                )
            clientsocket.sendto(ack.to_bytes(), server)
            print(
                f"[ACTIVE] ACK enviado a userId {user_id}: "
                f"{ack.to_string()}")
            
            if package.sequenceNumber == seq:  
                
                #Añadir rstrip con tamaño de paquete real.

                payload = package.payload
                f.write(payload)
                received_total+=len(payload)

                seq ^= 1 
            
            if package.fin:
                print(f"[ACTIVE] Paquete final de parte de {server} recibido.")
                print(f"Cantidad total recibida: {received_total}.")
                break 