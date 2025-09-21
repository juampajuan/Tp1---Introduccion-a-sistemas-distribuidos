import socket
import os
import struct
import threading
import sys
from segment import Segment, FLAG_SYN, FLAG_ACK, FLAG_FIN
from user_session import UserSession, OP_UPLOAD, OP_DOWNLOAD, STATE_CONNECTING, STATE_ACTIVE, STATE_DISCONNECTING, STATE_CONNECTION_CLOSED

# Constantes del tamanio del paquete
MAX_PACKET_SIZE = 400
USERID_SIZE = 2  # userId de 2 bytes (unsigned short)
OPERACION_SIZE = 1  # char
HEADER_SIZE = USERID_SIZE + OPERACION_SIZE
DATA_SIZE = MAX_PACKET_SIZE - HEADER_SIZE

# Mapa de usuarios: userId (int) -> UserSession
user_map = {}
user_map_lock = threading.Lock()

USERID_NUEVO_USUARIO = 0xFFFF
user_id_counter = 1

def generar_userid():
    global user_id_counter
    with user_map_lock:
        uid = user_id_counter
        user_id_counter = (user_id_counter + 1) & 0xFFFF  # Mantener en 2 bytes
    return uid

def procesar_paquete(data, addr, sock):
    # Usar Segment.from_bytes para decodificar el paquete recibido
    try:
        segment = Segment.from_bytes(data)
    except Exception as e:
        print(f"Error al decodificar el segmento: {e}")
        return
    userId = segment.userId
    operacion = segment.operacion
    payload = segment.payload
    flags = segment.flags
    syn = segment.get_flag(FLAG_SYN)
    ack = segment.get_flag(FLAG_ACK)
    fin = segment.get_flag(FLAG_FIN)

    if userId == USERID_NUEVO_USUARIO:
        nuevo_id = generar_userid()
        if operacion in (OP_UPLOAD, OP_DOWNLOAD):
            op_flag = operacion
        else:
            op_flag = -1  # Valor inválido
            print(f'Operación invalida recibida para nuevo usuario: {operacion}. Se descarta paquete')
            return
        nueva_sesion = UserSession(addr[0], addr[1], op_flag, STATE_CONNECTING)
        with user_map_lock:
            user_map[nuevo_id] = nueva_sesion
        print(f'Nuevo usuario registrado: userId={nuevo_id}, ip={addr[0]}, port={addr[1]}, operacion={op_flag}')
        # Responder al cliente con un segmento SYN+ACK y payload vacío
        respuesta_segment = Segment(nuevo_id, op_flag, syn=1, ack=0, fin=0, payload=b"")
        sock.sendto(respuesta_segment.to_bytes(), addr)
    else:
        with user_map_lock:
            usuario = user_map.get(userId)
        if usuario:
            # --- MATCH 1: syn=0, estado=STATE_CONNECTING, operacion=OP_DOWNLOAD ---
            if syn == 0 and usuario.estado == STATE_CONNECTING and usuario.operacion == OP_DOWNLOAD:
                usuario.estado = STATE_ACTIVE
                user_map[userId] = usuario  # Actualizar el estado en el mapa
                print(f"Se van a enviar datos al usuario: userId={userId}, ip={usuario.ip}, port={usuario.port}, operacion={usuario.operacion}, estado={usuario.estado}")
                # Enviar segmento ACK
                respuesta_segment = Segment(userId, usuario.operacion, syn=0, ack=1, fin=0, payload=b"")
                sock.sendto(respuesta_segment.to_bytes(), addr)
            # --- MATCH 2: syn=0, estado=STATE_CONNECTING, operacion=OP_UPLOAD ---
            elif syn == 0 and usuario.estado == STATE_CONNECTING and usuario.operacion == OP_UPLOAD:
                usuario.estado = STATE_ACTIVE
                user_map[userId] = usuario  # Actualizar el estado en el mapa
                print(f"Se van a recibir datos del usuario: userId={userId}, ip={usuario.ip}, port={usuario.port}, operacion={usuario.operacion}, estado={usuario.estado}")
                # Enviar segmento ACK
                respuesta_segment = Segment(userId, usuario.operacion, syn=0, ack=1, fin=0, payload=b"")
                sock.sendto(respuesta_segment.to_bytes(), addr)
            # --- MATCH 3: syn=0, estado=STATE_ACTIVE, ack=1 ---
            elif syn == 0 and usuario.estado == STATE_ACTIVE and ack == 1:
                print(f"Se recibe ACK del usuario: userId={userId}, ip={usuario.ip}, port={usuario.port}, operacion={usuario.operacion}, estado={usuario.estado}")
            else:
                print(f"Sesión encontrada para userId={userId}: ip={usuario.ip}, port={usuario.port}, operacion={usuario.operacion}, estado={usuario.estado}, falta manejar match para este caso")
        else:
            print(f"Usuario inválido: userId={userId}. Paquete descartado.")
            return

def start(host, port, storage):
    # Valida parametros de configuracion del server
    if host is None or port is None or storage is None:
        print('Error: Debe especificar host, port y storage.')
        sys.exit(1)

    # Si no existe el directorio de almacenamiento lo crea
    if not os.path.exists(storage):
        os.makedirs(storage)

    # Inicializar servidor UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((host, port))
    except Exception as e:
        print(f'Error al enlazar el socket UDP: {e}')
        sys.exit(1)

    print(f'Servidor UDP escuchando en {host}:{port}, almacenamiento en {storage}')
    while True:
        try:
            data, addr = sock.recvfrom(MAX_PACKET_SIZE)
            procesar_paquete(data, addr, sock)
        except KeyboardInterrupt:
            print('\nServidor detenido por el usuario.')
            break
        except Exception as e:
            print(f'Error al recibir datos: {e}')
