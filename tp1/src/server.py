import socket
import os
import threading

from lib.constants import ERROR_FALTA_CAMPO,ERROR_SERVICIO_INVALIDO, ERROR_PATH_INCORRECTO, ERROR_NOMBRE_INVALIDO,VALIDACION_OK,NOMBRES_RESERVADOS,CARACTERES_NO_PERMITIDOS
from lib.stop_and_wait import upload_stop_and_wait, download_stop_and_wait
from lib.selective_repeat import upload_selective_repeat, download_selective_repeat
from lib.packet import Packet
from lib.constants import MAX_UDP_PAYLOAD_LENGTH, PAYLOAD_SIZE
from user_session import UserSession
from queue import Empty

MAX_CANT_REVISADOS = 10
USER_ID_NUEVO = 65535
TIMEOUT = 1500/1000  # 1.5 segundos


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

def validar_pedido(packet):
    """
    Valida el payload con el pedido del cliente y extrae servicio, path, nombre y MTU.
    Devuelve una tupla:
    (1, "ERROR: Falta el campo <campo>") si falta un campo
    (2, "ERROR: servicio <valor> no valido") si el servicio no es válido
    (3, "ERROR: MTU <valor> no válido") si MTU no es mayor a 50
    (0, {"servicio":..., "path":..., "nombre":..., "MTU":...}) si el pedido es correcto
    """
    payload_str = packet.payload.rstrip(b'\x00').decode('utf-8').strip()
    fields = payload_str.split('\n')
    valores = {}
    for field in fields:
        if '|' in field:
            key, value = field.split('|', 1)
            valores[key] = value
    # Validar presencia de los 2 campos
    for campo in ["servicio", "nombre"]:
        if campo not in valores or not valores[campo]:
            return (ERROR_FALTA_CAMPO, f"ERROR: Falta el campo {campo} en el pedido de conexion")
    # Validar servicio
    servicio_valido = valores["servicio"] in ["sw", "sr", "dsw", "dsr"]
    if not servicio_valido:
        return ERROR_SERVICIO_INVALIDO, f"ERROR: servicio {valores['servicio']} no valido"
    # Si el pedido es correcto
    print(f"[ACTIVE] servicio: {valores['servicio']}, nombre: {valores['nombre']}")
    return VALIDACION_OK, valores


def validar_nombre(nombre):
    # 1) Validar caracteres no permitidos en el nombre
    for c in CARACTERES_NO_PERMITIDOS:
        if c in nombre:
            return (ERROR_NOMBRE_INVALIDO, f"Error: nombre de archivo invalido ({nombre})")
    # 2) Validar nombres reservados
    if nombre in NOMBRES_RESERVADOS:
        return (ERROR_NOMBRE_INVALIDO, f"Error: no se permiten archivos con el nombre {nombre}")
    # 3) Si pasa todas las validaciones
    return VALIDACION_OK, "OK"

def executing_protocol(protocol, user_session, user_id, file_name, storage, max_payload_size):
    if protocol in ["sw", "dsw"]:
        print(f"[ACTIVE] Iniciando protocolo Stop and Wait para userId {user_id}")
        if protocol == "sw":
            download_stop_and_wait(None, user_id, user_session.addr, storage + "/" + file_name, max_payload_size, from_server = True, user_session = user_session)
        else:
            upload_stop_and_wait(user_session.sock, user_id, user_session.addr, storage + "/" + file_name, max_payload_size, from_server = True, user_session = user_session)
    elif protocol in ["sr", "dsr"]:
        if protocol == "sr":
            download_selective_repeat(None, user_id, user_session.addr, storage + "/" + file_name, max_payload_size, from_server = True, user_session = user_session)
        else:
            upload_selective_repeat(user_session.sock, user_id, user_session.addr, storage + "/" + file_name, max_payload_size, from_server = True, user_session = user_session)

    else:
        print(f"Protocolo desconocido para userId {user_id}: {protocol}")
        return



def handle_session(user_session, packet_inicial, storage):

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
    timeout_handshake = 500/1000  # 0.5 segundos
    MAX_LOOPS = 10
    loops = 0
    waiting_sinack = False
    estado = user_session.get_estado()
    user_id = user_session.user_id
    packet = packet_inicial
    print(f"[HANDSHAKE] Packet inicial recibido: {packet.to_string()}")

    # Inicializar sequenceNumber del servidor para la sesión
    server_seq = 0
    client_seq = packet.sequence_number
    error_handshake = False

    while estado == Estado.SYNCING and loops < MAX_LOOPS:
        print(f"[HANDSHAKE] Iteración {loops+1} para userId {user_id}")
        print(f"[DEBUGGIG] Manejo de sesion usuario {user_session.user_id} - estado {user_session.get_estado()}")
        loops += 1
        if packet is not None and packet.connect == 1:
            print(f"[HANDSHAKE] Procesando paquete de userId {user_id}: {packet.to_string()}")
            if waiting_sinack:
                if packet.syn == 0 and packet.ack == 1:
                    # ACK final del cliente, handshake completo
                    print(f"Finaliza handshake para userId: {user_id}")
                    user_session.set_estado(Estado.ACTIVE)
                    estado = Estado.ACTIVE
                    continue
                # Retransmisión de SYN+ACK
                user_session.sock.sendto(response.toBytes(), user_session.addr)
                print(
                    f"Retransmitiendo SYNACK al usuario {user_id} "
                    f"(iteraciones: {loops})"
                )
            else:
                if packet.syn == 1 and packet.ack == 0:
                    # Primer SYN del cliente
                    client_seq = packet.sequence_number
                    # Validar cliente y extraer campos
                    res_val = validar_pedido(packet)
                    if res_val[0] == VALIDACION_OK:
                        #si es valido el modo de servicio
                        #queda validar nombre de archivo
                        nombre = res_val[1]["nombre"]
                        res_nombre = validar_nombre(nombre)
                        if res_nombre [0] == VALIDACION_OK:
                            #la solicitud es correcta envio sin + ack y OK
                            print(f"Pedido válido de userId {user_id}: servicio {res_val[1]} nombre {nombre}")
                            payload = f"OK".encode('utf-8')
                            response = Packet(
                                user_id,
                                payload=payload,
                                flags= (Packet.FLAG_CONNECT |
                                        Packet.FLAG_SYN |
                                        Packet.FLAG_ACK),
                                sequence_number=server_seq,
                                acknowledgment_number=client_seq + 1
                                )
                            print(
                                f"Enviando SYNACK+OK al usuario {user_id} "
                                f"(iteraciones: {loops})")
                            user_session.sock.sendto(response.toBytes(), user_session.addr)
                            waiting_sinack = True
                        else:
                            #hay un error en el nombre envio sin+ack+error
                            error_handshake = True
                            print(f"Error en el nombre del archivo para userId {user_id}: {res_nombre[1]}")
                            payload = res_nombre[1].encode('utf-8')
                            response = Packet(
                                user_id,
                                payload=payload,
                                flags= (Packet.FLAG_CONNECT |
                                        Packet.FLAG_SYN |
                                        Packet.FLAG_ACK),
                                sequence_number=server_seq,
                                acknowledgment_number=client_seq + 1
                                )
                            print(
                                f"Enviando SYNACK+ERROR al usuario {user_id} "
                                f"(iteraciones: {loops})")
                            user_session.sock.sendto(response.toBytes(), user_session.addr)
                            waiting_sinack = True
                    else:
                        #hay un error en el pedido
                        error_handshake = True
                        print(f"Pedido inválido de userId {user_id}: {res_val[1]}")
                        payload = res_val[1].encode('utf-8')
                        response = Packet(
                            user_id,
                            payload=payload,
                            flags= (Packet.FLAG_CONNECT |
                                    Packet.FLAG_SYN |
                                    Packet.FLAG_ACK),
                            sequence_number=server_seq,
                            acknowledgment_number=client_seq + len(payload.rstrip(b'\x00'))
                            )
                        print(
                            f"Enviando SYNACK+ERROR al usuario {user_id} "
                            f"(iteraciones: {loops})")
                        user_session.sock.sendto(response.toBytes(), user_session.addr)
                        waiting_sinack = True
        try:
            print(f"[HANDSHAKE] Esperando paquete de userId {user_id}...")
            packet = user_session.queue.get(timeout_handshake)
        except Empty:
            print(f"[HANDSHAKE] Timeout esperando paquete de userId {user_id}")
            packet = None

    if (user_session.get_estado() == Estado.SYNCING) or error_handshake:
        print(f"Fallo el handshake para el usuario {user_id}")
        return

    executing_protocol(res_val[1]["servicio"], user_session, user_id, res_val[1]["nombre"], storage, PAYLOAD_SIZE)


    print(f"Finalizando sesion para user: {user_id}, estado {user_session.get_estado()}")
    return

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
    sock.settimeout(None)
    try:
        sock.bind((host, port))
    except Exception as e:
        print(f'Error al enlazar el socket UDP: {e}')
        return
    print(f'Servidor UDP escuchando en {host}:{port}')
    server_sessions = {}
    try:
        while True:
            try:
                data, addr = sock.recvfrom(MAX_UDP_PAYLOAD_LENGTH)
            except socket.timeout:
                continue
            
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
                t = threading.Thread(target=handle_session,
                                     args=(user_session, packet, storage),
                                     daemon=True)
                t.start()
            elif user_id in server_sessions:
                user_session = server_sessions[user_id]
                user_session.queue.put(packet)
                # print(f"Paquete encolado para user_id {user_id}")
                # print(f"Paquete encolado: {packet.to_string()}")
            else:
                print(
                    f"Paquete descartado: user_id {user_id} "
                    f"no reconocido."
                )
    except KeyboardInterrupt:
        print("\nServidor detenido por el usuario.")
    except Exception as e:
        print(f"Error al recibir datos: {e}")