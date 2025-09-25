import socket
import os
import threading

from packet import Packet
from user_session import UserSession
from queue import Empty

MAX_PACKET_SIZE = 400
MAX_CANT_REVISADOS = 4
USER_ID_NUEVO = 65535
TIMEOUT = 1  # 1 segundo

user_id_counter = 1  # Comenzar en 1 para evitar colisión con 65535
user_id_lock = threading.Lock()


def generar_user_id():
    global user_id_counter
    with user_id_lock:
        user_id = user_id_counter
        user_id_counter += 1
        if user_id_counter >= USER_ID_NUEVO:
            user_id_counter = 1  # Reiniciar si se llega al máximo permitido
        return user_id


def abrir_archivo_usuario(storage, user_id):
    """Abre el archivo de usuario para escritura binaria y lo retorna."""
    filename = os.path.join(storage, f"user_{user_id}_file.txt")
    try:
        f = open(filename, "ab")  # Append binario
        print(f"Archivo abierto para userId {user_id}: {filename}")
        return f
    except Exception as e:
        print(f"Error al abrir el archivo para userId {user_id}: {e}")
        return None


def escribir_en_archivo_usuario(archivo, buffer, buffer_offset, fsync=False):
    """Escribe el contenido del buffer en el archivo y opcionalmente hace fsync."""
    if buffer_offset > 0:
        archivo.write(buffer[:buffer_offset])
        archivo.flush()
    if fsync:
        os.fsync(archivo.fileno())


def handleSession(user_session, packet_inicial, storage):
    """
    Handshake tipo TCP:
    - Espera un paquete con connect=1, syn=1, ack=0
    - Responde con connect=1, syn=1, ack=1
    - Espera confirmación con connect=1, syn=0, ack=1
    - Si se completa, pasa a estado ACTIVE
    - Si se itera más de tres veces sin finalizar handshake aborta
    Luego, si el estado es ACTIVE, recibe mensajes y responde con ACK.
    """
    from user_session import Estado
    TIMEOUT = 1  # 1 segundo
    MAX_LOOPS = 4

    loops = 0
    waiting_sinack = False
    estado = user_session.get_estado()
    user_id = user_session.user_id
    packet = packet_inicial

    print(f"[HANDSHAKE] Packet inicial recibido: {packet.to_string()}")

    # Inicializar sequenceNumber del servidor para la sesión
    server_seq = 0
    client_seq = packet.sequenceNumber

    # Buffer de 5MB para almacenar payloads
    BUFFER_SIZE = 5 * 1024 * 1024  # 5MB
    buffer = bytearray(BUFFER_SIZE)
    buffer_offset = 0
    archivo = None  # Solo abrir después del handshake

    while estado == Estado.SYNCING and loops < MAX_LOOPS:
        print(f"[HANDSHAKE] Iteración {loops+1} para userId {user_id}")
        loops += 1
        if packet is not None and packet.connect == 1:
            if waiting_sinack:
                if packet.syn == 0 and packet.ack == 1:
                    # ACK final del cliente, handshake completo
                    print(f"Finaliza handshake para userId: {user_id}")
                    user_session.set_estado(Estado.ACTIVE)
                    estado = Estado.ACTIVE
                    continue
                # Retransmisión de SYN+ACK
                response = Packet(
                    user_id,
                    flags=(Packet.FLAG_CONNECT |
                           Packet.FLAG_SYN |
                           Packet.FLAG_ACK),
                    sequenceNumber=server_seq,
                    acknowledgmentNumber=client_seq + 1
                )
                user_session.sock.sendto(response.toBytes(), user_session.addr)
                print(
                    f"Retransmitiendo SYNACK al usuario {user_id} "
                    f"(iteraciones: {loops})"
                )
            else:
                if packet.syn == 1 and packet.ack == 0:
                    # Primer SYN del cliente
                    client_seq = packet.sequenceNumber
                    response = Packet(
                        user_id,
                        flags=(Packet.FLAG_CONNECT |
                               Packet.FLAG_SYN |
                               Packet.FLAG_ACK),
                        sequenceNumber=server_seq,
                        acknowledgmentNumber=client_seq + 1
                    )
                    print(
                        f"Enviando SYNACK al usuario {user_id} "
                        f"(iteraciones: {loops})"
                    )
                    user_session.sock.sendto(
                        response.toBytes(), user_session.addr)
                    waiting_sinack = True
        try:
            print(f"[HANDSHAKE] Esperando paquete de userId {user_id}...")
            packet = user_session.queue.get(timeout=TIMEOUT)
        except Empty:
            print(f"[HANDSHAKE] Timeout esperando paquete de userId {user_id}")
            packet = None

    if user_session.get_estado() == Estado.SYNCING:
        print(f"Fallo el handshake para el usuario {user_id}")
        return

    # Abrir el archivo solo si el handshake fue exitoso
    archivo = abrir_archivo_usuario(storage, user_id)
    if archivo is None:
        print(f"No se pudo abrir archivo para userId {user_id}, abortando sesión.")
        return

    # Loop para probar que recibe mensajes del cliente y
    # envia un ack generico por cada uno,
    # si despues de 2 segundos no recibe nada cierra la sesion
    while user_session.get_estado() == Estado.ACTIVE:
        try:
            packet = user_session.queue.get(timeout=TIMEOUT)
            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{packet.to_string()}"
            )
            # Escribir el payload en el buffer
            payload = packet.payload.rstrip(b'\x00')
            payload_len = len(payload)
            if buffer_offset + payload_len <= BUFFER_SIZE:
                buffer[buffer_offset:buffer_offset+payload_len] = payload
                buffer_offset += payload_len
            else:
                # Buffer lleno, volcar al archivo y vaciar buffer
                escribir_en_archivo_usuario(archivo, buffer, buffer_offset, fsync=False)
                print(f"Buffer lleno, volcado al archivo para userId {user_id}")
                buffer_offset = 0
                # Escribir el nuevo payload en buffer vacío
                buffer[buffer_offset:buffer_offset+payload_len] = payload
                buffer_offset += payload_len
            # Enviar ACK (flag ACK activo)
            ack_packet = Packet(
                user_id,
                flags=Packet.FLAG_ACK,
                sequenceNumber=server_seq,
                acknowledgmentNumber=packet.sequenceNumber + payload_len
            )
            user_session.sock.sendto(ack_packet.toBytes(), user_session.addr)
            print(
                f"[ACTIVE] ACK enviado a userId {user_id}: "
                f"{ack_packet.to_string()}")
        except Empty:
            print(
                f"[ACTIVE] Timeout esperando mensaje de userId {user_id}, "
                f"cerrando sesión activa."
            )
            break

    # Al salir del while, si el buffer tiene datos, volcarlos al archivo y fsync
    escribir_en_archivo_usuario(archivo, buffer, buffer_offset, fsync=True)
    print(f"Buffer final guardado en archivo para userId {user_id}")
    archivo.close()
    print(f"Archivo cerrado para userId {user_id}")


def start(host, port, storage):
    # Validar y preparar la ruta de almacenamiento
    if not os.path.exists(storage):
        try:
            os.makedirs(storage)
            print(f'Directorio de almacenamiento creado: {storage}')
        except Exception as e:
            print(f'Error al crear el directorio de almacenamiento: {e}')
            return
    elif not os.path.isdir(storage):
        print(f'La ruta especificada no es un directorio: {storage}')
        return
    # Crear y enlazar el socket UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port))
    except Exception as e:
        print(f'Error al enlazar el socket UDP: {e}')
        return
    print(f'Servidor UDP escuchando en {host}:{port}')
    server_sessions = {}
    try:
        while True:
            data, addr = sock.recvfrom(MAX_PACKET_SIZE)
            try:
                packet = Packet.from_bytes(data)
                user_id = packet.userId
            except Exception as e:
                print(f"Error al decodificar paquete de {addr}: {e}")
                continue
            if user_id == USER_ID_NUEVO:
                nuevo_id = generar_user_id()
                user_session = UserSession(nuevo_id, addr, sock)
                server_sessions[nuevo_id] = user_session
                t = threading.Thread(target=handleSession,
                                     args=(user_session, packet, storage),
                                     daemon=True)
                t.start()
            elif user_id in server_sessions:
                user_session = server_sessions[user_id]
                user_session.queue.put(packet)
                print(f"Paquete encolado para user_id {user_id}")
            else:
                print(
                    f"Paquete descartado: user_id {user_id} "
                    f"no reconocido."
                )
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario.")
    except Exception as e:
        print(f"Error al recibir datos: {e}")
