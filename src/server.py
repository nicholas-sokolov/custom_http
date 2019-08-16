import email.utils
import logging
import mimetypes
import os
import posixpath
import select
import shutil
import socket
import time
import urllib
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
METHOD_NOT_ALLOWED = 405
INVALID_REQUEST = 422
INTERNAL_ERROR = 500
RESPONSE = {
    OK: 'OK',
    BAD_REQUEST: "Bad Request",
    FORBIDDEN: "Forbidden",
    NOT_FOUND: "Not Found",
    METHOD_NOT_ALLOWED: "Method Not Allowed",
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
    def __init__(self, server_address: tuple, handler, document_root=None, timeout=10, connect_now=True):
        self.server_address = server_address
        self.handler = handler
        self.document_root = document_root
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
        self.handler(request, client_address, self.document_root)


class CustomHTTPHandler:
    def __init__(self, connection, address, directory):
        self.connection = connection
        self.request_address = address
        self.directory = directory or os.getcwd()

        self.rfile = self.connection.makefile('rb', -1)
        self.wfile = _SocketWriter(self.connection)
        self.method = None
        self.path = None
        self.request_version = None
        self.close_connection = True
        self.raw_request_line = b''
        self._request_headers = {}
        self._response_headers_buffer = []
        self.handle()

    def handle(self):
        self.handle_request()
        while not self.close_connection:
            self.handle_request()

    def handle_request(self):
        self.raw_request_line = self.rfile.readline(65537)
        if len(self.raw_request_line) > 65536:
            return
        if not self.raw_request_line:
            self.close_connection = True
            return
        if not self.parse_request():
            return

        mname = f'do_{self.method}'
        if not hasattr(self, mname):
            self.send_response(METHOD_NOT_ALLOWED)
            self.flush_headers()
            return
        method = getattr(self, mname)
        method()
        self.wfile.flush()

    def parse_request(self):
        request_lines = self.raw_request_line.decode().split('\r\n')
        words = request_lines[0].split()

        if len(words) == 3:
            self.method, self.path, self.request_version = words
        elif len(words) == 2:
            self.method, self.path = words
        elif not words:
            return False
        else:
            self.send_response(BAD_REQUEST)
            return False

        self.parse_headers(self.raw_request_line)

        conntype = self._request_headers.get('Connection', "")
        if conntype.lower() == 'close':
            self.close_connection = True
        elif conntype.lower() == 'keep-alive':
            self.close_connection = False

        return True

    def parse_headers(self, request_data: bytes):
        request_lines = request_data.decode().split('\r\n')
        for line in request_lines[1:]:
            if not line:
                continue
            key, value = line.split(':')
            self._request_headers[key] = value.strip()

    def send_head(self):
        path = self.path.split('?', 1)[0]
        path = path.split('#', 1)[0]

        path = urllib.parse.unquote(path)
        path = posixpath.normpath(path)

        words = path.split('/')
        words = filter(None, words)
        path = ''
        for word in words:
            path = os.path.join(path, word)
        if self.path.rstrip().endswith('/'):
            path += os.path.sep
        path = os.path.join(self.directory, path)

        if not os.path.exists(path):
            self.send_response(NOT_FOUND)
            self.flush_headers()
            return
        if os.path.isdir(path):
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break

        base, ext = posixpath.splitext(path)
        extensions_map = mimetypes.types_map.copy()
        ctype = 'application/octet-stream'
        if ext in extensions_map:
            ctype = extensions_map[ext]

        try:
            f = open(path, 'rb')
        except OSError:
            self.send_response(NOT_FOUND)
            self.flush_headers()
            return

        try:
            self.send_response(OK)

            self.send_header("Content-type", ctype)
            fs = os.fstat(f.fileno())
            self.send_header("Content-Length", str(fs.st_size))
            # self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
            self.end_headers()
            return f
        except:
            f.close()
            raise

    def send_response(self, code, message=None):
        if message is None:
            message = RESPONSE[code]
        response = "{} {} {}\r\n".format(HTTP_VERSION, code, message)
        self._response_headers_buffer.append(response.encode('latin-1', 'strict'))

        self.send_header('Server', SERVER_NAME)
        self.send_header('Date', email.utils.formatdate(time.time(), usegmt=True))

    def send_header(self, keyword, value):
        line = f'{keyword}: {value}\r\n'.encode()
        self._response_headers_buffer.append(line)

    def end_headers(self):
        """Send the blank line ending the MIME headers."""
        self._response_headers_buffer.append(b"\r\n")
        self.flush_headers()

    def flush_headers(self):
        self.wfile.write(b"".join(self._response_headers_buffer))
        self._response_headers_buffer = []

    def do_GET(self):
        file = self.send_head()
        if not file:
            return
        try:
            shutil.copyfileobj(file, self.wfile)
        finally:
            file.close()

    def do_HEAD(self):
        """Serve a HEAD request."""
        file = self.send_head()
        if file:
            file.close()
