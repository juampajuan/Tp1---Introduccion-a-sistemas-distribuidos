from lib.constants import PACKET_HEADER_SIZE
from lib.packet import Packet
from lib.constants import PAYLOAD_SIZE

USERID_INICIAL = 65535  # User ID inicial para la handshake
TIMEOUT = 1

def separar_ruta(ruta):
    partes = ruta.rsplit('/', 1)
    
    if len(partes) == 2:
        path, filename = partes
    else:
        path = ''
        filename = partes[0]
    
    return path, filename


def handshake_with_server(clientsocket, server, servicio, nombre_archivo_server):
    clientsocket.settimeout(TIMEOUT)  # Timeout de 5 segundos
    payload_peticion = f"servicio|{servicio}\nnombre|{nombre_archivo_server}".encode("utf-8")
    out_packet = Packet(USERID_INICIAL, payload=payload_peticion, flags=Packet.FLAG_CONNECT | Packet.FLAG_SYN)
    max_envios = 3
    max_recvs = 10
    for intento_envio in range(max_envios):
        try:
            clientsocket.sendto(out_packet.toBytes(), server)
            print(f"[Handshake] Enviado paquete inicial, intento {intento_envio+1}/{max_envios}")
        except Exception as e:
            print(f"Error enviando paquete inicial: {e}")
            continue
        for intento_recv in range(max_recvs):
            try:
                data, _ = clientsocket.recvfrom(PACKET_HEADER_SIZE + PAYLOAD_SIZE)
                in_packet = Packet.from_bytes(data)
                user_id = in_packet.userId
                print(f"User ID asignado por el servidor: {user_id}\n")
                conexion_ok = recibir_detalles_conexion(in_packet.payload.decode("utf-8"))
                if conexion_ok:
                    ack = Packet(user_id, flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK)
                    clientsocket.sendto(ack.to_bytes(), server)
                    return user_id
                else:
                    print("Detalles de conexión inválidos. Abortando handshake actual.")
                    break  # Sale del ciclo interno y reintenta el envío externo
            except Exception as e:
                print(f"Error en handshake {e}")
                print(f"intento de recibir SIN+ACK: {intento_recv+1}/{max_recvs}")
                if intento_recv == max_recvs - 1:
                    print("No se recibió respuesta tras 10 intentos de recv. Reintentando envío inicial...")
        #no pudo recibir el user id, se vuelve a intentar el envio inicial
    print("No se pudo completar el handshake tras 3 intentos. Proceso abortado.")
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