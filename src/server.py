import socket
import logging

logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)
server_logger = logging.getLogger('server')

GET = 'GET'
HEAD = 'HEAD'
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
ERRORS = {
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}


class Server:

    SUPPORTED_METHODS = [GET, HEAD]

    def __init__(self, host, port, timeout=10, bind_and_activate=True):
        self.host = host
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.error = OK
        if bind_and_activate:
            self.server_bind()
            self.server_activate()

    def server_bind(self):
        self.socket.bind((self.host, self.port))

    def server_activate(self):
        self.socket.listen(5)
        conn, addr = self.socket.accept()
        # with conn:
        #     server_logger.info('Received connection from {}'.format(addr))
        while True:
            data = conn.recv(1024)
            if not data:
                break
            self.data_process(data)

    def close(self):
        self.socket.close()

    def data_process(self, data):
        method, path, protocol = data.decode().split('\r\n')[0].split()
        if method not in self.SUPPORTED_METHODS:
            self.error = INVALID_REQUEST
