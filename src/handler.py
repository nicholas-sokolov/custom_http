import os
import io
import sys
import html
import shutil
import email.utils
import time
from http import HTTPStatus

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


class CustomHTTPHandler:

    SUPPORTED_METHODS = [GET, HEAD]

    def __init__(self, socket, request_data, directory):
        # self.socket = socket
        self.request_data = request_data
        self.directory = directory
        self._headers_buffer = []
        self.wfile = socket.makefile('wb')

    def parse_request(self):
        pass

    def do_get(self, url):
        """ GET method

        :param str url:
        :return:
        """
        index_file = 'index.html'

        if url.endswith('/'):
            url = url[1:] + index_file

        path = '/'.join(self.directory.split('\\') + url.split('/'))
        if os.path.exists(path):
            code = HTTPStatus.OK
        else:
            code = HTTPStatus.NOT_FOUND

        body = b''
        if code == HTTPStatus.OK:
            with open(path) as f:
                content = ' '.join(f.readlines())
            body = content.encode('UTF-8', 'replace')
            # TODO: self.send_header("Content-Type", '')
            self.send_header('Content-Length', str(len(body)))
        self.wfile.write(body)

    def response(self):
        data_list = self.request_data.decode().split('\r\n')

        if not data_list or not data_list[0].strip():
            return

        method, url, version = data_list[0].split()

        if method not in self.SUPPORTED_METHODS:
            raise Exception('No such method!!!!')
        elif method == GET:
            self.do_get(url)

    def send_response_only(self, code, message=''):
        self._headers_buffer.append(("%s %d %s\r\n" % ("HTTP/1.0", code, message)).encode('latin-1', 'strict'))

    def _get_buffers(self):
        # TODO: Headers: Connection, Content‑Length, Content‑Type
        # TODO: Content‑Type for .html, .css, .js, .jpg, .jpeg, .png, .gif, .swf
        self.send_header('Server', 'MyCustomServer 0.1')
        self.send_header('Date', email.utils.formatdate(time.time(), usegmt=True))

    def send_header(self, keyword, value):
        """Send a MIME header to the headers buffer."""
        self._headers_buffer.append(("{}: {}\r\n".format(keyword, value)).encode())

    def flush_headers(self):
        self.wfile.write(b"".join(self._headers_buffer))
        self._headers_buffer = []
