import email.utils
import logging
import selectors
import socket
import time

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

select = selectors.DefaultSelector()

logging.basicConfig(format='[%(asctime)s] %(levelname).1s %(message)s',
                    datefmt='%Y.%m.%d %H:%M:%S',
                    level=logging.INFO)


class Server:
    def __init__(self, host, port, handler, timeout=10, bind_and_activate=True):
        self.host = host
        self.port = port
        self.handler = handler
        self.document_root = None
        self.timeout = timeout
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if bind_and_activate:
            self.server_bind_and_activate()

    def server_bind_and_activate(self):
        try:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            self.sock.bind((self.host, self.port))
            self.sock.listen(5)
            logging.info(f'Server activated on {self.host}:{self.port}')
        except socket.error as err:
            logging.error(f'{err}')
            raise Exception(err)

    def serve_forever(self):
        while True:
            try:
                conn, addr = self.sock.accept()
                self.handler(conn, addr)
            except socket.error as err:
                logging.error(f'{err}')
                self.sock.close()


class CustomHTTPHandler:
    def __init__(self, connection, address):
        self.connection = connection
        self.request_address = address
        self.method = None
        self.path = None
        self.body = ''
        self.raw_request_line = b''
        # TODO: Need use and clean
        self._request_headers = {}
        self._response_headers_buffer = []
        self.handle_request()

    def handle_request(self):
        while True:
            data = self.connection.recv(BUFFER_SIZE)
            if not data:
                break
            self.raw_request_line += data
        code = self.parse_request()
        self.response(code)

    def parse_request(self):
        if not self.raw_request_line:
            return False
        request_lines = self.raw_request_line.decode().split('\r\n')
        words = request_lines[0].split()

        if len(words) != 3:
            return BAD_REQUEST
        method, url, version = words
        if method not in SUPPORTED_METHODS:
            return NOT_FOUND

        self.parse_headers(self.raw_request_line)
        # TODO: 'Connection' handler
        return OK

    def parse_headers(self, request_data: bytes):
        request_lines = request_data.decode().split('\r\n')
        for line in request_lines[1:]:
            if not line:
                continue
            key, value = line.split(':')
            self._request_headers[key] = value.strip()

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
        self._response_headers_buffer.append(b"\r\n")
        self.flush_headers()

    def flush_headers(self):
        response_data = b''.join(self._response_headers_buffer)
        self.connection.send(response_data)
        self._response_headers_buffer = []
