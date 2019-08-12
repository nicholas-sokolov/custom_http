import email.utils
import logging
import selectors
import socket
import time
import types

from src.handler import CustomHTTPHandler

select = selectors.DefaultSelector()

logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)
server_logger = logging.getLogger('server')


class Server:

    def __init__(self, host, port, timeout=10, auto_connect=True, http_handler=CustomHTTPHandler):
        self.host = host
        self.port = port
        self.timeout = timeout
        self._socket = None
        if auto_connect:
            self.connect()

    def connect(self):
        try:
            if self._socket:
                self.close()
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_TCP, socket.TCP_NODELAY, 1)
            self._socket.connect((self.host, self.port))
            self._socket.settimeout(self.timeout)
        except socket.error as e:
            # TODO: catch this error and retry
            raise e

    def close(self):
        if self._socket:
            self._socket.close()
        self._socket = None
