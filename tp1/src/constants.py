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
WINDOWS_SIZE = 32
SEQUENCE_NUMBER_RANGE = 64