# todas las unidades medidas en bytes
SERVER_MTU = 700
FLAGS_SIZE = 1
USERID_SIZE = 2
SEQ_NUMBER_SIZE = 4
ACK_NUMBER_SIZE = 4
PACKET_HEADER_SIZE = (FLAGS_SIZE +
                      USERID_SIZE +
                      SEQ_NUMBER_SIZE +
                      ACK_NUMBER_SIZE)
MAX_PAYLOAD_SIZE = (SERVER_MTU -
                    PACKET_HEADER_SIZE -
                    28)  # 28 bytes para cabecera IP/UDP


VALIDACION_OK = 0
ERROR_FALTA_CAMPO = 1
ERROR_SERVICIO_INVALIDO = 2
ERROR_PATH_INCORRECTO = 3
ERROR_NOMBRE_INVALIDO = 4
ERROR_MTU_INVALIDO = 5

# Lista de caracteres no permitidos para nombres de archivo en Linux
CARACTERES_NO_PERMITIDOS = ['/', '\\', '\0', '*', '?', ':', '<', '>', '|', '"']

# Lista de nombres reservados para archivos en Linux (por conflicto o confusión)
NOMBRES_RESERVADOS = [
    '.', '..', 'bin', 'boot', 'dev', 'etc', 'home', 'lib', 'media', 'mnt', 'opt',
    'proc', 'root', 'run', 'sbin', 'srv', 'sys', 'tmp', 'usr', 'var',
    'ls', 'cat', 'echo', 'sh', 'bash', 'python', 'init', 'systemd', 'rc', 'service'
]

WINDOW_SIZE = 32
SEQUENCE_NUMBER_RANGE = 64