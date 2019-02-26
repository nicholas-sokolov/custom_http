import logging
import selectors
import socket
import types

select = selectors.DefaultSelector()

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
        self.timeout = timeout
        self.error = OK
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if bind_and_activate:
            self.server_bind()
            self.server_activate()

    def server_bind(self):
        self.socket.bind((self.host, self.port))

    def server_activate(self, poll_interval=0.5):
        self.socket.listen(0)
        server_logger.info("Listener was started on {} {}".format(self.host, self.port))
        self.socket.setblocking(False)
        select.register(self.socket, selectors.EVENT_READ)

        while True:
            events = select.select(poll_interval)
            for key, mask in events:
                if key.data is None:
                    self.accept_wrapper(key.fileobj)
                else:
                    self.service_connection(key, mask)

    @staticmethod
    def accept_wrapper(sock):
        conn, addr = sock.accept()  # Should be ready to read
        server_logger.info('Accepted connection from {}'.format(addr))
        conn.setblocking(False)
        data = types.SimpleNamespace(addr=addr, inb=b'', outb=b'')
        events = selectors.EVENT_READ | selectors.EVENT_WRITE
        select.register(conn, events, data=data)

    @staticmethod
    def service_connection(key, mask):
        sock = key.fileobj
        data = key.data
        if mask & selectors.EVENT_READ:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                data.outb += recv_data
            else:
                server_logger.info('Closing connection to {}'.format(data.addr))
                select.unregister(sock)
                sock.close()
        if mask & selectors.EVENT_WRITE:
            if data.outb:
                server_logger.info('Echoing {} to {}'.format(repr(data.outb), data.addr))
                sent = sock.send(data.outb)  # Should be ready to write
                data.outb = data.outb[sent:]

    def close(self):
        self.socket.close()
