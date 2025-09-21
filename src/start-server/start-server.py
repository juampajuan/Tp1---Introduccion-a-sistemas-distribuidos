#!/usr/bin/env python3
import argparse
import sys
from server import start


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

    start(args.host, args.port, args.storage)

if __name__ == '__main__':
    main()
