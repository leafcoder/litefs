#!/usr/bin/env python
# coding: utf-8

import argparse
import logging
import sys
from datetime import datetime
from posixpath import abspath as path_abspath
from watchdog.observers import Observer

from .cache import TreeCache, MemoryCache, FileEventHandler
from .request import RequestHandler, WSGIRequestHandler
from .server import HTTPServer, mainloop
from .utils import make_logger, log_error

__version__ = "0.3.0"


def make_config(**kwargs):
    default_config = vars(_cmd_args([]))
    default_config.update(kwargs)
    config = type('Config', (), default_config)
    config.webroot = path_abspath(config.webroot)
    return config


def make_server(host, port, request_size=-1):
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    if -1 == request_size:
        request_size = 1024
    sock.listen(request_size)
    sock.setblocking(0)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock


class Litefs(object):

    def __init__(self, **kwargs):
        self.config = config = make_config(**kwargs)
        level = logging.DEBUG if config.debug else logging.INFO
        self.logger = make_logger(__name__, log=config.log, level=level)
        self.host = host = config.host
        self.port = port = config.port
        self.server = None
        self.sessions = MemoryCache(max_size=1000000)
        self.caches = TreeCache()
        self.files = TreeCache()
        now = datetime.now().strftime("%B %d, %Y - %X")

    def wsgi(self):
        """
        返回符合 PEP 3333 规范的 WSGI application callable
        
        用法:
            import litefs
            app = litefs.Litefs(webroot='./site')
            application = app.wsgi()
            
        在 gunicorn 中使用:
            gunicorn -w 4 -b :8000 wsgi_example:application
            
        在 uWSGI 中使用:
            uwsgi --http :8000 --wsgi-file wsgi_example.py
        """
        def application(environ, start_response):
            """
            WSGI application callable
            
            Args:
                environ: WSGI 环境变量字典
                start_response: 开始响应的 callable
                
            Returns:
                可迭代的 bytes
            """
            try:
                request_handler = WSGIRequestHandler(self, environ)
                status, headers, content = request_handler.handler()
                start_response(status, headers)
                
                if isinstance(content, (list, tuple)):
                    result = []
                    for item in content:
                        if isinstance(item, str):
                            result.append(item.encode('utf-8'))
                        elif isinstance(item, bytes):
                            result.append(item)
                        else:
                            result.append(str(item).encode('utf-8'))
                    return result
                elif isinstance(content, str):
                    return [content.encode('utf-8')]
                elif isinstance(content, bytes):
                    return [content]
                else:
                    return [str(content).encode('utf-8')]
            except Exception as e:
                log_error(self.logger, str(e))
                status = '500 Internal Server Error'
                headers = [('Content-Type', 'text/plain; charset=utf-8')]
                start_response(status, headers)
                return [b'500 Internal Server Error']
        
        return application

    def handler(self, request, environ, server):
        from .server import SocketIO, BufferedRWPair, DEFAULT_BUFFER_SIZE
        raw = SocketIO(server, request)
        rw = BufferedRWPair(raw, raw, DEFAULT_BUFFER_SIZE)
        request_handler = RequestHandler(self, rw, environ, request)
        result = request_handler.handler()
        return request_handler.finish(result)

    def run(self, poll_interval=.2):
        observer = Observer()
        event_handler = FileEventHandler(self)
        observer.schedule(event_handler, self.config.webroot, True)
        observer.start()
        self.server = HTTPServer((self.host, self.port), self.handler)
        sys.stdout.write((
            "Litefs %s - %s\n"
            "Starting server at http://%s:%d/\n"
            "Quit the server with CONTROL-C.\n"
        ) % (__version__, datetime.now().strftime("%B %d, %Y - %X"), self.host, self.port))
        try:
            self.server.start()
            mainloop(poll_interval=poll_interval)
        except KeyboardInterrupt:
            pass
        except:
            log_error(self.logger)
        finally:
            observer.stop()
            observer.join()
            self.server.server_close()


def _cmd_args(args):
    title = args[0] if args else "litefs"
    parser = argparse.ArgumentParser(title, description=__doc__)
    parser.add_argument("-H", "--host", dest="host",
        required=False, default="localhost",
        help="bind server to HOST")
    parser.add_argument("-P", "--port", action="store", dest="port", type=int,
        required=False, default=9090,
        help="bind server to PORT")
    parser.add_argument("--webroot", dest="webroot",
        required=False, default="./site",
        help="use WEBROOT as root directory")
    parser.add_argument("--debug", action="store_true", dest="debug",
        required=False, default=False,
        help="start server in debug mode")
    parser.add_argument("--not-found", dest="not_found",
        required=False, default="not_found",
        help="use NOT_FOUND as 404 page")
    parser.add_argument("--default-page", dest="default_page",
        required=False, default="index.html",
        help="use DEFAULT_PAGE as web default page")
    parser.add_argument("--cgi-dir", dest="cgi_dir",
        required=False, default="/cgi-bin",
        help="use CGI_DIR as cgi scripts directory")
    parser.add_argument("--log", dest="log",
        required=False, default="./default.log",
        help="save log to LOG")
    parser.add_argument("--listen", dest="listen", type=int,
        required=False, default=1024,
        help="server LISTEN")
    args = parser.parse_args(args and args[1:])
    return args


def test_server():
    args = _cmd_args(sys.argv)
    kwargs = vars(args)
    litefs = Litefs(**kwargs)
    litefs.run(poll_interval=.1)


if "__main__" == __name__:
    test_server()
