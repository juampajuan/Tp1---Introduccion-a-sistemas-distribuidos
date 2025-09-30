from lib.constants import PACKET_HEADER_SIZE
from lib.packet import Packet
from lib.constants import PAYLOAD_SIZE

USERID_INICIAL = 65535  # User ID inicial para la handshake
TIMEOUT = 5

def separar_ruta(ruta):
    partes = ruta.rsplit('/', 1)
    
    if len(partes) == 2:
        path, filename = partes
    else:
        path = ''
        filename = partes[0]
    
    return path, filename


def handshake_with_server(clientsocket, server, servicio, path_para_server, nombre_archivo_server):

    clientsocket.settimeout(TIMEOUT)  # Timeout de 5 segundos
    
    # Arma y envia el paquete inicial con user_id=65535, flags CONNECT|SYN

    while True:
         
        try:
            payload_peticion = f"servicio|{servicio}\nnombre|{nombre_archivo_server}".encode("utf-8")
            out_packet = Packet(USERID_INICIAL, payload=payload_peticion, flags=Packet.FLAG_CONNECT | Packet.FLAG_SYN)
            clientsocket.sendto(out_packet.toBytes(), server)

            # Recibo el user_id asignado por el server
            data, _ = clientsocket.recvfrom(PACKET_HEADER_SIZE + PAYLOAD_SIZE)
            in_packet = Packet.from_bytes(data)
            user_id = in_packet.userId
            print(f"User ID asignado por el servidor: {user_id}\n")

            conexion_ok = recibir_detalles_conexion(in_packet.payload.decode("utf-8"))
            if conexion_ok:
                ack = Packet(user_id, flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK)
                clientsocket.sendto(ack.to_bytes(), server)
                return user_id
            #comentado porque mtu ya no se usa
            # mtu = recibir_detalles_conexion(in_packet.payload.decode("utf-8"))
            #
            # if mtu:
            #
            #     ack = Packet(user_id,flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK)
            #     clientsocket.sendto(ack.to_bytes(), server)
            #
            #     return user_id, mtu
        
        except Exception as e:
            print(f"Error durante el handshake con el servidor: {e}. Proceso abortado.")
            exit(1)


def recibir_detalles_conexion(payload):
     
    payload_filtrado = (payload).strip()
    payload_separado = payload_filtrado.split('\n')

    if payload_separado[0].startswith("Error:"):
        mensaje = payload_filtrado.split(":", 1)[1].strip()
        print(f"Error: {mensaje}")
        exit(1)
    #edito esta linea porque ya no viene el mtu en el payload, solo ok o error
    #elif len(payload_separado) == 2 and payload_separado[0] == "OK":
    elif payload_separado[0] == "OK":
        print("Handshake completado exitosamente.")
        return True

        #ya no se usa mtu
        # if payload_separado[1].startswith("MTU="):
        #     mtu_str = payload_separado[1].split("=")[1].replace('\x00', '').strip()
        #     mtu = int(mtu_str)
        #     print(f"Mtu retornado: {mtu}.")
        #
        #     return mtu

    print("Formato de respuesta del server invalido, esperando nuevo mensaje")
    return False