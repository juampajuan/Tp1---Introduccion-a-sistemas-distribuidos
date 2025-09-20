#!/usr/bin/env python3
import argparse
import sys
import socket
import os
import struct
import threading

# Constantes del tamanio del paquete
MAX_PACKET_SIZE = 400
USERID_SIZE = 2  # userId de 2 bytes (unsigned short)
OPERACION_SIZE = 1  # char
HEADER_SIZE = USERID_SIZE + OPERACION_SIZE
DATA_SIZE = MAX_PACKET_SIZE - HEADER_SIZE

# Mapa de usuarios: userId (int) -> {'ip': str, 'port': int, 'operacion': str}
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
    if len(data) < HEADER_SIZE:
        print(f'Paquete demasiado pequeño de {addr}')
        return
    # extrae userId (2 bytes) y operacion (char) usando endian por defecto
    userId, operacion = struct.unpack('H1s', data[:HEADER_SIZE])
    operacion = operacion.decode('utf-8')
    payload = data[HEADER_SIZE:]
    print(f'Recibido paquete de {addr}: userId={userId}, operacion={operacion}, data_len={len(payload)})')

    if userId == USERID_NUEVO_USUARIO:
        nuevo_id = generar_userid()
        with user_map_lock:
            user_map[nuevo_id] = {
                'ip': addr[0],
                'port': addr[1],
                'operacion': operacion
            }
        print(f'Nuevo usuario registrado: userId={nuevo_id}, ip={addr[0]}, port={addr[1]}, operacion={operacion}')
        # Responder al cliente con el nuevo userId (2 bytes) usando endian por defecto
        respuesta = struct.pack('H', nuevo_id)
        sock.sendto(respuesta, addr)
    else:
        # Mostrar datos del usuario y el payload como texto
        with user_map_lock:
            usuario = user_map.get(userId)
        print(f'Usuario existente: userId={userId}, ip={addr[0]}, port={addr[1]}, operacion={operacion}')
        if usuario:
            print(f'Datos usuario registrados: {usuario}')
        try:
            texto = payload.decode('utf-8')
        except UnicodeDecodeError:
            texto = payload.decode('latin1', errors='replace')
        print(f'Payload recibido (texto): {texto}')

def main():
    parser = argparse.ArgumentParser(
        prog='start-server',
        description='Servicio de almacenamiento y descarga de archivos.'
    )
    parser.add_argument('-v', '--verbose', action='store_true', help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true', help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, metavar='ADDR', help='service IP address')
    parser.add_argument('-P', '--port', type=int, metavar='PORT', help='service port')
    parser.add_argument('-s', '--storage', type=str, metavar='DIRPATH', help='storage dir path')

    args = parser.parse_args()

    # Valida parametros de configuracion del server
    if args.host is None or args.port is None or args.storage is None:
        print('Error: Debe especificar --host, --port y --storage.')
        parser.print_help()
        sys.exit(1)

    # Si no existe el directorio de almacenamiento lo crea
    if not os.path.exists(args.storage):
        os.makedirs(args.storage)

    # Inicializar servidor UDP
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.bind((args.host, args.port))
    except Exception as e:
        print(f'Error al enlazar el socket UDP: {e}')
        sys.exit(1)

    print(f'Servidor UDP escuchando en {args.host}:{args.port}, almacenamiento en {args.storage}')
    while True:
        try:
            data, addr = sock.recvfrom(MAX_PACKET_SIZE)
            procesar_paquete(data, addr, sock)
        except KeyboardInterrupt:
            print('\nServidor detenido por el usuario.')
            break
        except Exception as e:
            print(f'Error al recibir datos: {e}')

if __name__ == '__main__':
    main()
