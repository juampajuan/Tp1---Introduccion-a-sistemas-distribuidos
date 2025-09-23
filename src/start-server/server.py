import socket
import os
import threading

from packet import Packet
from user_session import UserSession
from queue import Empty

MAX_PACKET_SIZE = 400
MAX_CANT_REVISADOS = 4
USER_ID_NUEVO = 65535
TIMEOUT = 2

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


def handleSession(user_session, packet_inicial):
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
    TIMEOUT = 2
    MAX_LOOPS = 4

    loops = 0
    waiting_sinack = False
    estado = user_session.get_estado()
    user_id = user_session.user_id
    packet = packet_inicial

    while estado == Estado.SYNCING and loops < MAX_LOOPS:
        loops += 1
        if packet is not None and packet.connect == 1:
            # Si no es un paquete connect no tiene sentido
            # revisarlo en este punto
            if waiting_sinack:
                if packet.syn == 0 and packet.ack == 1:
                    print(f"Finaliza handshake para userId: {user_id}")
                    user_session.set_estado(Estado.ACTIVE)
                    estado = Estado.ACTIVE
                    continue
                # Si no es el paquete esperado, reenviar syn=1, ack=1
                response = Packet(
                    user_id,
                    flags=(Packet.FLAG_CONNECT |
                           Packet.FLAG_SYN |
                           Packet.FLAG_ACK)
                )
                user_session.sock.sendto(response.toBytes(), user_session.addr)
                print(
                    f"Enviando SYNACK al usuario {user_id} "
                    f"(iteraciones: {loops})"
                )
            else:
                if packet.syn == 1 and packet.ack == 0:
                    response = Packet(
                        user_id,
                        flags=(Packet.FLAG_CONNECT |
                               Packet.FLAG_SYN |
                               Packet.FLAG_ACK)
                    )
                    print(
                        f"Enviando SYNACK al usuario {user_id} "
                        f"(iteraciones: {loops})"
                    )
                    user_session.sock.sendto(response.toBytes(),
                                             user_session.addr)
                    waiting_sinack = True
        try:
            packet = user_session.queue.get(timeout=TIMEOUT)
        except Empty:
            packet = None

    if user_session.get_estado() == Estado.SYNCING:
        print(f"Fallo el handshake para el usuario {user_id}")
        return

    # Loop para probar que recibe mensajes del cliente y envia un ack
    # generico por cada uno,
    # si despues de 2 segundos no recibe nada cierra la sesion
    while user_session.get_estado() == Estado.ACTIVE:
        try:
            packet = user_session.queue.get(timeout=TIMEOUT)
            print(
                f"[ACTIVE] Recibido de userId {user_id}: "
                f"{packet.to_string()}"
            )
            # Enviar ACK (flag ACK activo)
            ack_packet = Packet(user_id, flags=Packet.FLAG_ACK)
            user_session.sock.sendto(ack_packet.toBytes(), user_session.addr)
            print(f"[ACTIVE] ACK enviado a userId {user_id}")
        except Empty:
            print(
                f"[ACTIVE] Timeout esperando mensaje de userId {user_id}, "
                f"cerrando sesión activa."
            )
            break


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
                                     args=(user_session, packet),
                                     daemon=True)
                t.start()
            elif user_id in server_sessions:
                user_session = server_sessions[user_id]
                user_session.queue.put(packet)
            else:
                print(
                    f"Paquete descartado: user_id {user_id} "
                    f"no reconocido."
                )
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario.")
    except Exception as e:
        print(f"Error al recibir datos: {e}")
