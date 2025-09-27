from constants import MAX_PACKET_SIZE
from packet import Packet
USERID_INICIAL = 65535  # User ID inicial para la handshake
TIMEOUT = 5


def handshake_with_server(clientsocket, server, servicio, path_archivo_server, nombre_archivo_server):

    clientsocket.settimeout(TIMEOUT)  # Timeout de 5 segundos
    
    # Arma y envia el paquete inicial con user_id=65535, flags CONNECT|SYN

    while True:
         
        try:
            payload_peticion = f"servicio|{servicio}\npath|{path_archivo_server}\nnombre|{nombre_archivo_server}"
            out_packet = Packet(USERID_INICIAL, payload=payload_peticion, flags=Packet.FLAG_CONNECT | Packet.FLAG_SYN)
            clientsocket.sendto(out_packet.toBytes(), server)

            # Recibo el user_id asignado por el server
            data, _ = clientsocket.recvfrom(MAX_PACKET_SIZE) 
            in_packet = Packet.from_bytes(data)
            user_id = in_packet.userId
            print(f"User ID asignado por el servidor: {user_id}\n")

            mtu = recibir_detalles_conexion(in_packet.payload, clientsocket, server)

            return user_id, mtu
        
        except Exception as e:
            print(f"Error durante el handshake con el servidor: {e}. Proceso abortado.")
            exit(1)


def recibir_detalles_conexion(payload, clientsocket, server):
     
        payload_filtrado = (payload).strip()
        payload_separado = payload_filtrado.split('\n')

        if payload_separado.startswith("Error:"):
            mensaje = payload_filtrado.split(":", 1)[1].strip()
            print(f"Error: {mensaje}")
            exit(1)

        elif len(payload_separado) == 2 and payload_separado[0] == "OK":

            if payload_separado[1].startswith("MTU:"):
                    
                mtu = int(payload_separado[1].split(":")[1].strip())
                print(f"Mtu retornado: {mtu}.")

                ack = Packet(flags=Packet.FLAG_ACK)
                clientsocket.sendto(ack.to_bytes(), server)

                return mtu     

        else:
            print("Formato de respuesta del server invalido, esperando nuevo mensaje")