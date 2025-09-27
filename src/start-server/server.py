import socket
import os
import threading

from constants import ERROR_FALTA_CAMPO,ERROR_SERVICIO_INVALIDO, ERROR_PATH_INCORRECTO, ERROR_NOMBRE_INVALIDO,VALIDACION_OK,NOMBRES_RESERVADOS,CARACTERES_NO_PERMITIDOS
from constants import SERVER_MTU
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
    # Validar presencia de los cuatro campos
    for campo in ["servicio", "path", "nombre", "MTU"]:
        if campo not in valores or not valores[campo]:
            return (ERROR_FALTA_CAMPO, f"ERROR: Falta el campo {campo} en el pedido de conexion")
    # Validar servicio
    servicio_valido = valores["servicio"] in ["sw", "sr", "dsw", "dsr"]
    if not servicio_valido:
        return (ERROR_SERVICIO_INVALIDO, f"ERROR: servicio {valores['servicio']} no valido")
    # Validar MTU mayor a 50
    try:
        mtu_val = int(valores["MTU"])
        if mtu_val <= 50:
            return (5, f"ERROR: MTU {mtu_val} no válido, debe ser mayor a 50")
    except ValueError:
        return (5, f"ERROR: MTU {valores['MTU']} no es un número válido")
    # Si el pedido es correcto
    print(f"[ACTIVE] servicio: {valores['servicio']}, path: {valores['path']}, nombre: {valores['nombre']}, MTU: {valores['MTU']}")
    return (VALIDACION_OK, valores)


def validar_ruta_y_nombre(nombre, ruta, storage):
    # 1) Validar caracteres no permitidos en el nombre
    for c in CARACTERES_NO_PERMITIDOS:
        if c in nombre:
            return (ERROR_NOMBRE_INVALIDO, f"Error: nombre de archivo invalido ({nombre})")
    # 2) Validar nombres reservados
    if nombre in NOMBRES_RESERVADOS:
        return (ERROR_NOMBRE_INVALIDO, f"Error: no se permiten archivos con el nombre {nombre}")
    # 3) Validar ruta
    if ruta != storage:
        return (ERROR_PATH_INCORRECTO, "Error: path incorrecto")
    # 4) Si pasa todas las validaciones
    return VALIDACION_OK, "OK"


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

    res_packet = None
    payload =""
    loops = 0
    waiting_sinack = False
    estado = user_session.get_estado()
    user_id = user_session.user_id
    packet = packet_inicial
    ruta=""
    nombre=""
    print(f"[HANDSHAKE] Packet inicial recibido: {packet.to_string()}")

    # Inicializar sequenceNumber del servidor para la sesión
    server_seq = 0
    client_seq = packet.sequenceNumber
    client_mtu = 0
    # Buffer de 5MB para almacenar payloads
    BUFFER_SIZE = 5 * 1024 * 1024  # 5MB
    buffer = bytearray(BUFFER_SIZE)
    buffer_offset = 0
    archivo = None  # Solo abrir después del handshake
    error_handshake = False


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
                user_session.sock.sendto(response.toBytes(), user_session.addr)
                print(
                    f"Retransmitiendo SYNACK al usuario {user_id} "
                    f"(iteraciones: {loops})"
                )
            else:
                if packet.syn == 1 and packet.ack == 0:
                    # Primer SYN del cliente
                    client_seq = packet.sequenceNumber
                    # Validar cliente y extraer campos
                    res_val = validar_pedido(packet)
                    if res_val[0] == VALIDACION_OK:
                        #si es valido el modo de servicio
                        #queda validar nombe y path
                        ruta = res_val[1]["path"]
                        nombre = res_val[1]["nombre"]
                        client_mtu = res_val[1]["MTU"]
                        res_ruta_y_nombre = validar_ruta_y_nombre(ruta, nombre,storage)
                        if res_ruta_y_nombre [0] == VALIDACION_OK:
                            #la solicitud es correcta envio sin + ack y OK
                            print(f"Pedido válido de userId {user_id}: servicio {res_val[1]}, path {ruta}, nombre {nombre}")
                            payload = f"OK\nMTU={SERVER_MTU}".encode('utf-8')
                            response = Packet(
                                user_id,
                                payload,
                                flags= (Packet.FLAG_CONNECT |
                                        Packet.FLAG_SYN |
                                        Packet.FLAG_ACK),
                                sequenceNumber=server_seq,
                                acknowledgmentNumber=client_seq + len(payload.rstrip(b'\x00'))
                                )
                            print(
                                f"Enviando SYNACK+OK al usuario {user_id} "
                                f"(iteraciones: {loops})")
                            user_session.sock.sendto(response.toBytes(), user_session.addr)
                        else:
                            #hay un error en el nombre o el path envion sin+ack+error
                            error_handshake = True
                            print(f"Error en el nombre o path del archivo para userId {user_id}: {res_ruta_y_nombre[1]}")
                            payload = res_ruta_y_nombre[1].encode('utf-8')
                            response = Packet(
                                user_id,
                                payload,
                                flags= (Packet.FLAG_CONNECT |
                                        Packet.FLAG_SYN |
                                        Packet.FLAG_ACK),
                                sequenceNumber=server_seq,
                                acknowledgmentNumber=client_seq + len(payload.rstrip(b'\x00'))
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
                            payload,
                            flags= (Packet.FLAG_CONNECT |
                                    Packet.FLAG_SYN |
                                    Packet.FLAG_ACK),
                            sequenceNumber=server_seq,
                            acknowledgmentNumber=client_seq + len(payload.rstrip(b'\x00'))
                            )
                        print(
                            f"Enviando SYNACK+ERROR al usuario {user_id} "
                            f"(iteraciones: {loops})")
                        user_session.sock.sendto(response.toBytes(), user_session.addr)
                        waiting_sinack = True
        try:
            print(f"[HANDSHAKE] Esperando paquete de userId {user_id}...")
            packet = user_session.queue.get(timeout=TIMEOUT)
        except Empty:
            print(f"[HANDSHAKE] Timeout esperando paquete de userId {user_id}")
            packet = None

    if (user_session.get_estado() == Estado.SYNCING) or error_handshake:
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
