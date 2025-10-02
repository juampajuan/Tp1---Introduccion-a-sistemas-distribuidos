from .constants import PACKET_HEADER_SIZE
from .packet import Packet
from .constants import PAYLOAD_SIZE
import logging

USERID_INICIAL = 65535  # User ID inicial para la handshake
TIMEOUT = 1

logger = logging.getLogger("HANDSHAKE-WITH-SERVER")


def separar_ruta(ruta):
    partes = ruta.rsplit('/', 1)

    if len(partes) == 2:
        path, filename = partes
    else:
        path = ''
        filename = partes[0]

    return path, filename


def handshake_with_server(
        clientsocket,
        server,
        servicio,
        nombre_archivo_server):
    clientsocket.settimeout(TIMEOUT)  # Timeout de 5 segundos
    payload_peticion = f"servicio|{servicio}\nnombre|{
        nombre_archivo_server}".encode("utf-8")
    out_packet = Packet(
        USERID_INICIAL,
        payload=payload_peticion,
        flags=Packet.FLAG_CONNECT | Packet.FLAG_SYN)
    max_envios = 3
    max_recvs = 10
    for intento_envio in range(max_envios):
        try:
            clientsocket.sendto(out_packet.toBytes(), server)
            logger.info(
                f"[Handshake] Enviado paquete inicial, intento {
                    intento_envio + 1}/{max_envios}")
        except Exception as e:
            logger.error(f"Error enviando paquete inicial: {e}")
            continue
        for intento_recv in range(max_recvs):
            try:
                data, _ = clientsocket.recvfrom(
                    PACKET_HEADER_SIZE + PAYLOAD_SIZE)
                in_packet = Packet.from_bytes(data)
                user_id = in_packet.userId
                logger.info(f"User ID asignado por el servidor: {user_id}\n")
                conexion_ok = recibir_detalles_conexion(
                    in_packet.payload.decode("utf-8"))
                if conexion_ok:
                    ack = Packet(
                        user_id, flags=Packet.FLAG_CONNECT | Packet.FLAG_ACK)
                    clientsocket.sendto(ack.to_bytes(), server)
                    return user_id
                else:
                    logger.error(
                        "Detalles de conexión inválidos."
                        " Abortando handshake actual.")
                    break
                    # Sale del ciclo interno y reintenta # el envío externo
            except Exception as e:
                logger.error(f"Error en handshake {e}")
                logger.debug(
                    f"intento de recibir "
                    f"SIN+ACK: {intento_recv + 1}/{max_recvs}")
                if intento_recv == max_recvs - 1:
                    logger.debug(
                        "No se recibió respuesta tras 10 intentos de recv."
                        " Reintentando envío inicial...")
        # no pudo recibir el user id, se vuelve a intentar el envio inicial
    logger.error(
        "No se pudo completar el handshake tras 3 intentos. Proceso abortado.")
    exit(1)


def recibir_detalles_conexion(payload):

    payload_filtrado = (payload).strip()
    payload_separado = payload_filtrado.split('\n')

    if payload_separado[0].startswith("Error:"):
        mensaje = payload_filtrado.split(":", 1)[1].strip()
        logger.error(f"Error: {mensaje}")
        exit(1)
    elif payload_separado[0] == "OK":
        logger.info("Handshake completado exitosamente.")
        return True

    logger.error(
        "Formato de respuesta del server invalido, esperando nuevo mensaje")
    return False
