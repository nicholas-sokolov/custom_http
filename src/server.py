import email.utils
import logging
import select
import socket
import time
import os
import shutil
from socketserver import _SocketWriter

SERVER_NAME = 'MyCustomServer 0.1'
HTTP_VERSION = 'HTTP/1.1'
BUFFER_SIZE = 1024
GET = 'GET'
HEAD = 'HEAD'
SUPPORTED_METHODS = (GET, HEAD)
OK = 200
BAD_REQUEST = 400
FORBIDDEN = 403
NOT_FOUND = 404
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
RESPONSE = {
    OK: 'OK',
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    INVALID_REQUEST: "Invalid Request",
    INTERNAL_ERROR: "Internal Server Error",
}

# Default error message template
DEFAULT_ERROR_MESSAGE = """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN"
        "http://www.w3.org/TR/html4/strict.dtd">
<html>
    <head>
        <meta http-equiv="Content-Type" content="text/html;charset=utf-8">
        <title>Error response</title>
    </head>
    <body>
        <h1>Error response</h1>
        <p>Error code: %(code)d</p>
        <p>Message: %(message)s.</p>
        <p>Error code explanation: %(code)s - %(explain)s.</p>
    </body>
</html>
"""

logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)


class Server:
    def __init__(self, server_address: tuple, handler, timeout=10, connect_now=True):
        self.server_address = server_address
        self.handler = handler
        self.document_root = None
        self.timeout = timeout
        self._socket = None
        if connect_now:
            try:
                self.connect()
            except:
                self.close()
                raise

    def connect(self):
        try:
            if self._socket:
                self.close()
            self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._socket.bind(self.server_address)
            self.server_address = self._socket.getsockname()
            self._socket.listen(5)
            logging.info(f'Server activated on {self.server_address}')
        except socket.error as e:
            # TODO: catch this error and retry
            logging.error(f'{e}')
            raise e

    def close(self):
        if self._socket:
            self._socket.close()
        self._socket = None

    def fileno(self):
        return self._socket.fileno()

    def serve_forever(self, poll_interval=0.5):
        while True:
            try:
                r, w, e = select.select([self], [], [], poll_interval)
                if self in r:
                    self.handle_request()
            except socket.error as err:
                logging.error(f'{err}')
                self._socket.close()

    def handle_request(self):
        request, client_address = self._socket.accept()
        self.handler(request, client_address)


class CustomHTTPHandler:
    def __init__(self, connection, address):
        self.connection = connection
        self.request_address = address
        self.rfile = self.connection.makefile('rb', -1)
        self.wfile = _SocketWriter(self.connection)
        self.directory = os.getcwd()

        self.method = None
        self.path = None
        self.body = ''
        self.raw_request_line = b''
        # TODO: Need use and clean
        self._request_headers = {}
        self._response_headers_buffer = []
        self.handle_request()

    def handle_request(self):
        self.raw_request_line = self.rfile.readline(65537)
        if not self.raw_request_line:
            return
        code = self.parse_request()
        self.response(code)

    def parse_request(self):
        if not self.raw_request_line:
            return False
        request_lines = self.raw_request_line.decode().split('\r\n')
        words = request_lines[0].split()

        if len(words) != 3:
            return BAD_REQUEST
        method, self.url, version = words

        if method not in SUPPORTED_METHODS:
            return NOT_FOUND

        self.parse_headers(self.raw_request_line)

        if method == GET:
            self.do_GET()

        return OK

    def parse_headers(self, request_data: bytes):
        request_lines = request_data.decode().split('\r\n')
        for line in request_lines[1:]:
            if not line:
                continue
            key, value = line.split(':')
            self._request_headers[key] = value.strip()

    def send_head(self):
        path = self.directory

        words = self.url.split('/')
        words = filter(None, words)
        for word in words:
            path = os.path.join(path, word)

        if not os.path.exists(path):
            raise Exception()
        if os.path.isdir(path):
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
        try:
            f = open(path, 'rb')
        except OSError:
            self.response(NOT_FOUND)
            return None
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        return f

    def response(self, code):
        """ Prepare headers for response and response """
        logging.info(f'Response Code:{code}')
        self.send_simple_response(code, HTTP_VERSION, RESPONSE[code])
        # TODO: Headers: Connection
        # TODO: Content‑Type for .html, .css, .js, .jpg, .jpeg, .png, .gif, .swf
        self.send_header('Server', SERVER_NAME)
        self.send_header('Date', email.utils.formatdate(time.time(), usegmt=True))
        self.end_headers()

    def send_simple_response(self, code, version, message=''):
        response = "{} {} {}\r\n".format(version, code, message)
        self._response_headers_buffer.append(response.encode('latin-1', 'strict'))

    def send_header(self, keyword, value):
        line = f'{keyword}: {value}'.encode()
        self._response_headers_buffer.append(line)

    def end_headers(self):
        """Send the blank line ending the MIME headers."""
        self._response_headers_buffer.append(b"\r\n\r\n")
        self.flush_headers()

    def flush_headers(self):
        response_data = b''.join(self._response_headers_buffer)
        self.connection.sendall(response_data)
        self.connection.close()
        self._response_headers_buffer = []

    def do_GET(self):
        file = self.send_head()
        if not file:
            return
        try:
            shutil.copyfileobj(file, self.wfile)
        finally:
            file.close()

