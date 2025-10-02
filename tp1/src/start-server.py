#!/usr/bin/env python3
import argparse
import sys
from lib.server import start
import logging

logger = logging.getLogger("START-SERVER")


def main():
    parser = argparse.ArgumentParser(
        prog='start-server',
        description='Servicio de almacenamiento y descarga de archivos.'
    )
    parser.add_argument('-v', '--verbose', action='store_true',
                        help='increase output verbosity')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='decrease output verbosity')
    parser.add_argument('-H', '--host', type=str, metavar='ADDR',
                        help='service IP address')
    parser.add_argument('-p', '--port', type=int, metavar='PORT',
                        help='service port')
    parser.add_argument('-s', '--storage', type=str, metavar='DIRPATH',
                        help='storage dir path')

    args = parser.parse_args()

    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='[%(name)s][%(levelname)s] %(message)s')

    # Valida parametros de configuracion del server
    if args.host is None or args.port is None or args.storage is None:
        logger.error('Error: Debe especificar --host, --port y --storage.')
        parser.print_help()
        sys.exit(1)

    start(args.host, args.port, args.storage)


if __name__ == '__main__':
    main()
