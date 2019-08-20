import os
import multiprocessing
import argparse
from src.server import Server, CustomHTTPHandler

def start_server(address, workers):
    servers = []
    try:
        for worker in range(workers):
            server = Server(address, CustomHTTPHandler)
            p = multiprocessing.Process(target=server.serve_forever)
            servers.append(p)
            p.start()
        for proc in servers:
            proc.join()
    except KeyboardInterrupt:
        for process in servers:
            if not process:
                continue
            pid = process.pid
            print(pid)
            process.terminate()
            print('rewrwe')


if __name__ == '__main__':

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
    start_server(server_address, int(args.w))
