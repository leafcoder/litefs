#!/usr/bin/env python
# coding: utf-8

import logging
import socket
import sys
from errno import ENOTCONN, EMFILE, EWOULDBLOCK, EAGAIN, EPIPE
from functools import partial
from io import RawIOBase, BufferedRWPair, DEFAULT_BUFFER_SIZE
from posixpath import abspath as path_abspath, join as path_join
from traceback import print_exc

try:
    from greenlet import greenlet, getcurrent, GreenletExit
    HAS_GREENLET = True
except ImportError:
    HAS_GREENLET = False
    greenlet = None
    getcurrent = None
    GreenletExit = None

try:
    from select import EPOLLIN, EPOLLOUT, EPOLLHUP, EPOLLERR, EPOLLET, \
        epoll as select_epoll
    HAS_EPOLL = True
except (ImportError, AttributeError):
    HAS_EPOLL = False
    EPOLLIN = EPOLLOUT = EPOLLHUP = EPOLLERR = EPOLLET = 0
    select_epoll = None

from .request import RequestHandler, parse_form
from .exceptions import HttpError
from .utils import log_error

should_retry_error = (EWOULDBLOCK, EAGAIN)


def make_headers(rw):
    headers = {}
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    s = s.decode("utf-8")
    while True:
        if s in ("", "\n", "\r\n"):
            break
        k, v = s.split(":", 1)
        k, v = k.lower().strip(), v.strip()
        headers[k] = v
        s = rw.readline(DEFAULT_BUFFER_SIZE)
        s = s.decode("utf-8")
    return headers


def make_environ(server, rw, client_address):
    environ = dict()
    environ["SERVER_NAME"] = server.server_name
    environ["SERVER_SOFTWARE"] = "litefs/0.3.0"
    environ["SERVER_PORT"] = server.server_port
    environ["REMOTE_ADDR"] = client_address
    environ["REMOTE_HOST"] = client_address[0]
    environ["REMOTE_PORT"] = client_address[1]
    
    from urllib.parse import unquote_plus
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    s = s.decode("utf-8")
    if not s:
        raise HttpError("invalid http headers")
    request_method, path_info, protocol = s.strip().split()
    if "?" in path_info:
        path_info, query_string = path_info.split("?", 1)
    else:
        path_info, query_string = path_info, ""
    path_info = unquote_plus(path_info)
    base_uri, script_name = path_info.split("/", 1)
    if "" == script_name:
        script_name = "index.html"
    environ["REQUEST_METHOD"] = request_method.upper()
    environ["QUERY_STRING"] = unquote_plus(query_string)
    environ["SERVER_PROTOCOL"] = protocol
    environ["SCRIPT_NAME"] = script_name
    environ["PATH_INFO"] = path_info
    headers = make_headers(rw)
    length = headers.get("content-length")
    if length:
        environ["CONTENT_LENGTH"] = length = int(length)
    content_type = headers.get("content-type")
    if content_type:
        environ["CONTENT_TYPE"] = content_type
    else:
        environ["CONTENT_TYPE"] = content_type = "text/plain; charset=utf-8"
    
    try:
        from cgi import parse_header
    except ImportError:
        from email.message import Message
        def parse_header(line):
            msg = Message()
            msg['content-type'] = line
            return msg.get_params()[0], dict(msg.get_params()[1:])
    
    _, params = parse_header(content_type)
    charset = params.get('charset')
    environ['CHARSET'] = charset
    for k, v in headers.items():
        k = k.replace("-", "_").upper()
        if k in environ:
            continue
        environ[k] = v
    
    return environ


class SocketIO(RawIOBase):

    def __init__(self, server, sock):
        RawIOBase.__init__(self)
        self._fileno = sock.fileno()
        self._sock = sock
        self._server = server

    def fileno(self):
        return self._fileno

    def readable(self):
        return True

    def writable(self):
        return True

    def readinto(self, b):
        real_epoll = epoll._epoll
        fileno = self._fileno
        curr = getcurrent()
        self.read_gr = curr
        if self.write_gr is None:
            real_epoll.register(fileno, EPOLLIN | EPOLLET)
        else:
            real_epoll.modify(fileno, EPOLLIN | EPOLLOUT | EPOLLET)
        data = b""
        try:
            curr.parent.switch()
            data = self._sock.recv(len(b))
        except socket.error as e:
            if e.errno not in should_retry_error:
                raise
        finally:
            self.read_gr = None
            if self.write_gr is None:
                real_epoll.unregister(fileno)
            else:
                real_epoll.modify(fileno, EPOLLOUT | EPOLLET)
        n = len(data)
        try:
            b[:n] = data
        except TypeError as err:
            import array
            if not isinstance(b, array.array):
                raise err
            b[:n] = array.array(b"b", data)
        return n

    def write(self, data):
        real_epoll = epoll._epoll
        fileno = self._fileno
        curr = getcurrent()
        self.write_gr = curr
        if self.read_gr is None:
            real_epoll.register(fileno, EPOLLOUT | EPOLLET)
        else:
            real_epoll.modify(fileno, EPOLLIN | EPOLLOUT | EPOLLET)
        try:
            curr.parent.switch()
            return self._sock.send(data)
        except socket.error as e:
            if e.errno not in should_retry_error:
                raise
        finally:
            self.write_gr = None
            if self.read_gr is None:
                real_epoll.unregister(fileno)
            else:
                real_epoll.modify(fileno, EPOLIN | EPOLLET)

    def close(self):
        if self.closed:
            return
        RawIOBase.close(self)
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            if e.errno != ENOTCONN:
                raise
        self._sock.close()

    read_gr = write_gr = None


class Epoll(object):

    def __init__(self):
        self._epoll = select_epoll()
        self._servers = {}
        self._greenlets = {}
        self._idels = []

    def register(self, server_socket):
        servers = self._servers
        fileno = server_socket.fileno()
        servers[fileno] = server_socket
        self._epoll.register(fileno, EPOLLIN | EPOLLET)

    def unregister(self, server_socket):
        servers = self._servers
        fileno = server_socket.fileno()
        if fileno in servers:
            self._epoll.unregister(fileno)
            del servers[fileno]

    def close(self):
        for fileno, server_socket in self._servers.items():
            self._epoll.unregister(fileno)
            server_socket.server_close()
        self._epoll.close()

    def poll(self, poll_interval=.2):
        servers = self._servers
        greenlets = self._greenlets
        _poll = self._epoll.poll
        idels = self._idels
        while True:
            events = _poll(poll_interval)
            for fileno, event in events:
                if fileno in servers:
                    server = servers[fileno]
                    try:
                        server.handle_request()
                    except KeyboardInterrupt:
                        break
                    except socket.error as e:
                        if e.errno == EMFILE:
                            raise
                        print_exc()
                    except:
                        print_exc()
                elif (event & EPOLLIN) or (event & EPOLLOUT):
                    try:
                        greenlets[fileno].switch()
                    except KeyboardInterrupt:
                        break
                    except:
                        print_exc()
                elif event & (EPOLLHUP | EPOLLERR):
                    try:
                        greenlets[fileno].throw()
                    except KeyboardInterrupt:
                        break
                    except:
                        print_exc()
            while len(idels):
                from time import time
                now_ts = time()
                ts, gr = idels.pop(0)
                if ts > now_ts:
                    idels.append((ts, gr))
                    idels.sort()
                    break
                else:
                    gr.switch()


class TCPServer(object):
    """Classic Python TCPServer"""

    allow_reuse_address = True
    request_queue_size = 4194304
    address_family, socket_type = socket.AF_INET, socket.SOCK_STREAM

    def __init__(self, server_address, RequestHandlerClass,
                       bind_and_activate=True):
        self.server_address = server_address
        self.RequestHandlerClass = RequestHandlerClass
        self.socket = socket.socket(self.address_family,
                                    self.socket_type)
        self._started = False
        if bind_and_activate:
            try:
                self.server_bind()
                self.server_activate()
            except:
                self.server_close()
                raise

    def server_bind(self):
        if self.allow_reuse_address:
            self.socket.setsockopt(socket.SOL_SOCKET,
                                   socket.SO_REUSEADDR, 1)
        self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logging.info("bind %s:%s", *self.server_address)
        self.socket.bind(self.server_address)
        self.socket.setblocking(0)

    def server_activate(self):
        self.socket.listen(self.request_queue_size)

    def server_close(self):
        self.socket.close()

    def fileno(self):
        return self.socket.fileno()

    def get_request(self):
        return self.socket.accept()

    def handle_request(self):
        self._handle_request_noblock()

    def _handle_request_noblock(self):
        while True:
            try:
                request, client_address = self.get_request()
            except socket.error as e:
                errno = e.args[0]
                if EAGAIN == errno or EWOULDBLOCK == errno:
                    return
                raise
            if self.verify_request(request, client_address):
                try:
                    self.process_request(request, client_address)
                except:
                    self.handle_error(request, client_address)
                    self.shutdown_request(request)
            else:
                self.shutdown_request(request)

    def handle_timeout(self):
        pass

    def verify_request(self, request, client_address):
        return True

    def process_request(self, request, client_address):
        try:
            self.finish_request(request, client_address)
        except:
            self.handle_error(request, client_address)
            self.shutdown_request(request)

    def finish_request(self, request, client_address):
        request.setblocking(0)
        fileno = request.fileno()
        epoll._greenlets[fileno] = curr = greenlet(
            partial(self._finish_request, request, client_address)
        )
        curr.switch()

    def _finish_request(self, request, client_address):
        raw = SocketIO(self, request)
        try:
            rw = BufferedRWPair(raw, raw, DEFAULT_BUFFER_SIZE)
            environ = make_environ(self, rw, client_address)
            self.RequestHandlerClass(request, environ, self)
            self.shutdown_request(request)
        except socket.error as e:
            if e.errno == EPIPE:
                raise GreenletExit
            raise
        except Exception as e:
            if not isinstance(e, HttpError):
                raise
        finally:
            try:
                if raw.read_gr is not None:
                    raw.read_gr.throw()
                if raw.write_gr is not None:
                    raw.write_gr.throw()
            finally:
                fileno = raw.fileno()
                epoll._greenlets.pop(fileno, None)
            if not raw.closed:
                try:
                    raw.close()
                except:
                    pass

    def shutdown_request(self, request):
        try:
            request.shutdown(socket.SHUT_WR)
        except OSError:
            pass
        self.close_request(request)

    def close_request(self, request):
        request.close()

    def handle_error(self, request, client_address):
        import traceback
        traceback.print_exc()

    def server_forever(self, poll_interval=.1):
        if not self._started:
            epoll.register(self)
        mainloop(poll_interval=poll_interval)

    def start(self):
        if not self._started:
            epoll.register(self)
            self._started = True

    def shutdown(self):
        if self._started:
            epoll.unregister(self)
            self._started = False


class HTTPServer(TCPServer):

    allow_reuse_address = 1

    def server_bind(self):
        TCPServer.server_bind(self)
        host, port = self.socket.getsockname()[:2]
        self.server_name = socket.getfqdn(host)
        self.server_port = port


class WSGIServer(HTTPServer):

    application = None

    def server_bind(self):
        HTTPServer.server_bind(self)
        self.setup_environ()

    def setup_environ(self):
        env = {}
        env["SERVER_NAME"] = self.server_name
        env["GATEWAY_INTERFACE"] = "CGI/1.1"
        env["SERVER_PORT"] = str(self.server_port)
        env["REMOTE_HOST"] = ""
        env["CONTENT_LENGTH"] = -1
        env["SCRIPT_NAME"] = ""
        self.base_environ = env

    def get_app(self):
        return self.application

    def set_app(self, application):
        self.application = application


def mainloop(poll_interval=.1):
    try:
        epoll.poll(poll_interval=poll_interval)
    except KeyboardInterrupt:
        pass
    finally:
        epoll.close()


server_forever = mainloop

epoll = Epoll() if HAS_EPOLL else None
