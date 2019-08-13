import os

from src.server import Server, CustomHTTPHandler

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument('-w', help='Number of workers')
    parser.add_argument('--bind', '-b', default='127.0.0.1', metavar='ADDRESS',
                        help='Specify alternate bind address '
                             '[default: all interfaces]')
    parser.add_argument('-r', default=os.getcwd(),
                        help='Specify alternative directory '
                             '[default:current directory]')
    parser.add_argument('port', action='store',
                        default=80, type=int,
                        nargs='?',
                        help='Specify alternate port [default: 8000]')
    args = parser.parse_args()
    server_address = args.bind, args.port
    server = Server(server_address, CustomHTTPHandler)
    server.serve_forever()
