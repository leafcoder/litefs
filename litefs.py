#!/usr/bin/env python
# coding: utf-8

import argparse
import cgi
import itertools
import json
import logging
import re
import sqlite3
import sys

from collections import deque
from datetime import datetime
from errno import ENOTCONN, EMFILE, EWOULDBLOCK, EAGAIN, EPIPE
from functools import partial
from greenlet import greenlet, getcurrent, GreenletExit
from gzip import GzipFile
from hashlib import sha1
from imp import find_module, load_module, new_module as imp_new_module
from io import RawIOBase, BufferedRWPair, DEFAULT_BUFFER_SIZE
from mako import exceptions
from mako.lookup import TemplateLookup
from mimetypes import guess_type
from os import urandom, stat
from posixpath import join as path_join, splitext as path_splitext, \
    split as path_split, realpath as path_realpath, \
    abspath as path_abspath, isfile as path_isfile, \
    isdir as path_isdir, exists as path_exists
from select import EPOLLIN, EPOLLOUT, EPOLLHUP, EPOLLERR, EPOLLET, \
    epoll as select_epoll
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile, TemporaryFile
from time import time, strftime, gmtime
from traceback import print_exc
from uuid import uuid4
from watchdog.events import *
from watchdog.observers import Observer
from weakref import proxy
from zlib import compress

PY3 = sys.version_info.major > 2

if PY3:
    # Import modules in py3
    import socket
    from collections import UserDict
    from http.client import responses as http_status_codes
    from http.cookies import SimpleCookie
    from io import BytesIO as StringIO
    from urllib.parse import splitport, unquote_plus

    def is_unicode(s):
        return isinstance(s, str)

    def is_bytes(s):
        return isinstance(s, bytes)

    imap = map
else:
    # Import modules in py2
    import _socket as socket
    from cStringIO import StringIO
    from httplib import responses as http_status_codes
    from itertools import imap
    from urllib import splitport, unquote_plus
    from Cookie import SimpleCookie
    from UserDict import UserDict

    def is_unicode(s):
        return isinstance(s, unicode)

    def is_bytes(s):
        return isinstance(s, basestring)

__doc__ = """\
Build a web server framework using Python. Litefs was developed to imple\
ment a server framework that can quickly, securely, and flexibly build Web \
projects. Litefs is a high-performance HTTP server. Litefs has the characte\
ristics of high stability, rich functions, and low system consumption.

Author: leafcoder
Email: leafcoder@gmail.com

Copyright (c) 2020, Leafcoder.
License: MIT (see LICENSE for details)
"""

__version__ = "0.3.0"
__license__ = "MIT"
__author__ = "Leafcoder"

server_software = "litefs/%s" % __version__

default_page = "index.html"
default_404 = "not_found"
default_sid = "litefs.sid"
default_content_type = "text/plain; charset=utf-8"

EOFS = ("", "\n", "\r\n")
POSTS_HEADER_NAME = "litefs.posts"
FILES_HEADER_NAME = "litefs.files"
date_format = "%Y/%m/%d %H:%M:%S"
should_retry_error = (EWOULDBLOCK, EAGAIN)
double_slash_sub = re.compile(r"\/{2,}").sub
startswith_dot_sub = re.compile(r"\/\.+").sub
suffixes = (".py", ".pyc", ".pyo", ".so", ".mako")
cgi_suffixes = (".pl", ".py", ".pyc", ".pyo", ".php")
form_dict_match = re.compile(r"(.+)\[([^\[\]]+)\]").match
server_info = "litefs/%s python/%s" % (__version__, sys.version.split()[0])
cgi_runners = {
    ".pl": "/usr/bin/perl",
    ".py": "/usr/bin/python",
    ".pyc": "/usr/bin/python",
    ".pyo": "/usr/bin/python",
    ".php": "/usr/bin/php"
}

DEFAULT_STATUS_MESSAGE = """\
<html>
    <head>
        <meta charset="utf-8">
        <title>HTTP response</title>
    </head>
    <body>
        <h1>HTTP response</h1>
        <p>HTTP status %(code)d.
        <p>Message: %(message)s.
        <p>HTTP code explanation: %(code)s = %(explain)s.
    </body>
</html>"""


def log_error(logger, message=None):
    if message is None:
        message = "error occured"
    logger.error(message, exc_info=True)


def log_info(logger, message=None):
    if message is None:
        message = "info"
    logger.info(message)


def log_debug(logger, message=None):
    if message is None:
        message = "debug"
    logger.debug(message)


class HttpError(Exception):
    pass


def render_error():
    return exceptions.html_error_template().render()


def gmt_date(timestamp=None):
    if timestamp is None:
        timestamp = time()
    return strftime("%a, %d %b %Y %H:%M:%S GMT", gmtime(timestamp))


def new_module(**kwargs):
    """创建新模块

    新创建的模块不会加入到 sys.path 中，并导入自定义属性。
    """
    name = "".join(("litefs", uuid4().hex))
    module = imp_new_module(name)
    module.__dict__.update(kwargs)
    return module


def make_config(**kwargs):
    default_config = vars(_cmd_args([]))
    default_config.update(kwargs)
    config = new_module(**default_config)
    config.webroot = path_abspath(config.webroot)
    return config


def make_logger(name, log=None, level=logging.DEBUG):
    """创建日志对象

    输出 HTTP 访问日志和错误异常。
    """
    logger = logging.getLogger(name)
    fmt = logging.Formatter(
        ("%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message"
         ")s"),
        datefmt=date_format
    )
    logger.setLevel(level)
    if log:
        handler = logging.FileHandler(log)
        handler.setFormatter(fmt)
        logger.addHandler(handler)
    handler = logging.StreamHandler()
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger


def make_server(host, port, request_size=-1):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    if -1 == request_size:
        request_size = 1024
    sock.listen(request_size)
    sock.setblocking(0)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock


def make_headers(rw):
    """Read and parse HTTP headers from RWPair object"""
    headers = {}
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    if PY3:
        s = s.decode("utf-8")
    while True:
        if s in EOFS:
            break
        k, v = s.split(":", 1)
        k, v = k.lower().strip(), v.strip()
        headers[k] = v
        s = rw.readline(DEFAULT_BUFFER_SIZE)
        if PY3:
            s = s.decode("utf-8")
    return headers


def make_environ(server, rw, client_address):
    environ = dict()
    environ["SERVER_NAME"] = server.server_name
    environ["SERVER_SOFTWARE"] = server_software
    environ["SERVER_PORT"] = server.server_port
    environ["REMOTE_ADDR"] = client_address
    environ["REMOTE_HOST"] = client_address[0]
    environ["REMOTE_PORT"] = client_address[1]
    # Read first line
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    if PY3:
        s = s.decode("utf-8")
    if not s:
        # It means server is waiting for reading when getting empty string.
        raise HttpError("invalid http headers")
    request_method, path_info, protocol = s.strip().split()
    if "?" in path_info:
        path_info, query_string = path_info.split("?", 1)
    else:
        path_info, query_string = path_info, ""
    path_info = unquote_plus(path_info)
    base_uri, script_name = path_info.split("/", 1)
    if "" == script_name:
        script_name = default_page
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
        environ["CONTENT_TYPE"] = content_type = default_content_type
    _, params = cgi.parse_header(content_type)
    charset = params.get('charset')
    environ['CHARSET'] = charset
    for k, v in headers.items():
        k = k.replace("-", "_").upper()
        # Skip content_length, content_type, etc.
        if k in environ:
            continue
        k = "HTTP_%s" % k
        if k in environ:
            environ[k] += ",%s" % v  # Comma-separate multiple headers
        else:
            environ[k] = v
    if not length:
        return environ
    content_type = environ.get("CONTENT_TYPE", "")
    if content_type.startswith("multipart/form-data"):
        posts, files = parse_multipart(rw, content_type)
        environ[POSTS_HEADER_NAME] = posts
        environ[FILES_HEADER_NAME] = files
    else:
        environ["POST_CONTENT"] = post_content = rw.read(int(length))
        if PY3:
            environ["POST_CONTENT"] \
                = unquote_plus(post_content.decode("utf-8"))
    # Body will be empty when CONTENT_LENGTH equals to -1
    environ.setdefault('CONTENT_LENGTH', -1)
    for k in ("HTTP_USER_AGENT", "HTTP_COOKIE", "HTTP_REFERER"):
        environ.setdefault(k, "")
    return environ


def parse_multipart(rw, content_type):
    boundary = content_type.split("=")[1].strip()
    if PY3:
        boundary = boundary.encode("utf-8")
    begin_boundary = (b"--%s" % boundary)
    end_boundary = (b"--%s--" % boundary)
    posts = {}
    files = {}
    s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
    while True:
        if s.strip() != begin_boundary:
            assert s.strip() == end_boundary
            break
        headers = {}
        s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
        while s:
            if PY3:
                s = s.decode("utf-8")
            k, v = s.split(":", 1)
            headers[k.strip().upper()] = v.strip()
            s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
        disposition = headers["CONTENT-DISPOSITION"]
        disposition, params = cgi.parse_header(disposition)
        name = params["name"]
        filename = params.get("filename")
        if filename:
            fp = TemporaryFile(mode="w+b")
            s = rw.readline(DEFAULT_BUFFER_SIZE)
            while s.strip() != begin_boundary \
                    and s.strip() != end_boundary:
                fp.write(s)
                s = rw.readline(DEFAULT_BUFFER_SIZE)
            fp.seek(0)
            files[name] = fp
        else:
            fp = StringIO()
            s = rw.readline(DEFAULT_BUFFER_SIZE)
            while s.strip() != begin_boundary \
                    and s.strip() != end_boundary:
                fp.write(s)
                s = rw.readline(DEFAULT_BUFFER_SIZE)
            fp.seek(0)
            posts[name] = fp.getvalue().strip().decode('utf-8')
    return posts, files


def parse_form(query_string):
    form = {}
    query_string = unquote_plus(query_string)
    for s in query_string.split("&"):
        if not s:
            continue
        kv = s.split("=", 1)
        if 2 == len(kv):
            k, v = kv
        else:
            k, v = kv[0], ""
        k, v = unquote_plus(k), unquote_plus(v)
        if k.endswith("[]"):
            k = k[:-2]
            if k in form:
                result = form[k]
                if isinstance(result, dict):
                    raise ValueError("invalid form data %s" % query_string)
                if isinstance(result, list):
                    form[k].append(v)
                else:
                    form[k] = [result, v]
            else:
                form[k] = [v]
            continue
        matched = form_dict_match(k)
        if matched is None:
            if k in form:
                result = form[k]
                if isinstance(result, dict):
                    raise ValueError("invalid form data %s" % query_string)
                if isinstance(result, list):
                    form[k].append(v)
                else:
                    form[k] = [result, v]
            else:
                form[k] = v
        else:
            key, prefix = matched.groups()
            if key in form:
                result = form[key]
                if not isinstance(result, dict):
                    raise ValueError("invalid form data %s" % query_string)
                if prefix in result:
                    result[prefix] = [result[prefix], v]
                else:
                    result[prefix] = v
            else:
                form[key] = {prefix: v}
    return form

class FileEventHandler(FileSystemEventHandler):

    def __init__(self, app):
        FileSystemEventHandler.__init__(self)
        self._app = proxy(app)

    def on_moved(self, event):
        src_path = event.src_path
        dest_path = event.dest_path
        webroot = self._app.config.webroot
        if webroot == src_path and event.is_directory:
            return
        if not src_path.startswith(webroot + "/"):
            return
        if webroot == dest_path and event.is_directory:
            return
        if not dest_path.startswith(webroot + "/"):
            return
        log_info(self._app.logger, "%s has been moved to %s" \
            % (src_path, dest_path))
        src_path = "/%s" % src_path[len(webroot):].strip("/")
        dest_path = "/%s" % dest_path[len(webroot):].strip("/")
        caches = self._app.caches
        files = self._app.files
        caches.delete(src_path)
        files.delete(src_path)
        caches.delete(dest_path)
        files.delete(dest_path)
        src_path, suffix = path_splitext(src_path)
        if suffix in suffixes:
            caches.delete(src_path)
            files.delete(src_path)
        dest_path, suffix = path_splitext(dest_path)
        if suffix in suffixes:
            caches.delete(dest_path)
            files.delete(dest_path)

    def on_created(self, event):
        src_path = event.src_path
        webroot = self._app.config.webroot
        if webroot == src_path and event.is_directory:
            return
        if not src_path.startswith(webroot + "/"):
            return
        log_info(self._app.logger, "%s has been modified" % src_path)
        src_path = "/%s" % src_path[len(webroot):].strip("/")
        caches = self._app.caches
        files = self._app.files
        caches.delete(src_path)
        files.delete(src_path)
        src_path, suffix = path_splitext(src_path)
        if suffix in suffixes:
            caches.delete(src_path)
            files.delete(src_path)

    on_modified = on_deleted = on_created


class LiteFile(object):

    def __init__(self, path, base, name, text, status_code=200):
        self.status_code = int(status_code)
        self.path = path
        self.text = text
        self.etag = etag = sha1(text).hexdigest()
        self.zlib_text = zlib_text = compress(text, 9)[2:-4]
        self.zlib_etag = sha1(zlib_text).hexdigest()
        stream = StringIO()
        with GzipFile(fileobj=stream, mode="wb") as f:
            f.write(text)
        self.gzip_text = gzip_text = stream.getvalue()
        self.gzip_etag = sha1(gzip_text).hexdigest()
        self.last_modified = gmt_date(stat(path).st_mtime)
        mimetype, coding = guess_type(name)
        headers = [("Content-Type", "text/html;charset=utf-8")]
        if mimetype is not None:
            headers = [("Content-Type", "%s;charset=utf-8" % mimetype)]
        headers.append(("Last-Modified", self.last_modified))
        headers.append(("Connection", "close"))
        self.headers = headers

    def handler(self, request):
        environ = request.environ
        if_modified_since = environ.get("HTTP_IF_MODIFIED_SINCE")
        if if_modified_since == self.last_modified:
            return request._response(304)
        if_none_match = environ.get("HTTP_IF_NONE_MATCH")
        accept_encodings = environ.get(
            "HTTP_ACCEPT_ENCODING", "").split(",")
        accept_encodings = [s.strip().lower() for s in accept_encodings]
        headers = list(self.headers)
        if "gzip" in accept_encodings:
            if if_none_match == self.gzip_etag:
                return request._response(304)
            headers.append(("Etag", self.gzip_etag))
            headers.append(("Content-Encoding", "gzip"))
            text = self.gzip_text
        elif "deflate" in accept_encodings:
            if if_none_match == self.zlib_etag:
                return request._response(304)
            headers.append(("Etag", self.zlib_etag))
            headers.append(("Content-Encoding", "deflate"))
            text = self.zlib_text
        else:
            if if_none_match == self.etag:
                return request._response(304)
            headers.append(("Etag", self.etag))
            text = self.text
        headers.append(("Content-Length", "%d" % len(text)))
        return request._response(
            self.status_code, headers=headers, content=text)


class TreeCache(object):

    def __init__(self, clean_period=60, expiration_time=3600):
        self.data = {}
        self.clean_time = time()
        self.clean_period = clean_period
        self.expiration_time = expiration_time
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.text_factory = str
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS cache (
                key VARCHAR PRIMARY KEY,
                timestamp INTEGER
            );
            CREATE INDEX idx_cache ON cache (key);
        """)

    def __len__(self):
        return len(self.data)

    def put(self, key, val):
        conn = self.conn
        data = self.data
        if self.clean_time + self.clean_period < time():
            self.auto_clean()
        timestamp = int(time())
        if key not in data:
            conn.execute("""
                INSERT INTO cache (key, timestamp) VALUES (?, ?);
            """, (key, timestamp))
        else:
            conn.execute("""
                UPDATE cache SET timestamp=? WHERE key=?;
            """, (timestamp, key))
        data[key] = [val, timestamp]

    def get(self, key):
        data = self.data
        if self.clean_time + self.clean_period < time():
            self.auto_clean()
        ret = data.get(key)
        if ret is None:
            return None
        val, timestamp = ret
        if int(time() - timestamp) > self.expiration_time:
            del data[key]
            return None
        return val

    def delete(self, key):
        conn = self.conn
        data = self.data
        if self.clean_time + self.clean_period < time():
            self.auto_clean()
        curr = conn.execute("""\
            SELECT key FROM cache WHERE key=? OR key LIKE ?;
        """, (key, key + "/%"))
        keys = curr.fetchall()
        conn.executemany("""\
            DELETE FROM cache WHERE key=?;
        """, keys)
        for item in keys:
            key = item[0]
            del data[key]

    def auto_clean(self):
        conn = self.conn
        data = self.data
        last_expiration_time = int(time() - self.expiration_time)
        curr = conn.execute("""
            SELECT key FROM cache WHERE timestamp < ?;
        """, (last_expiration_time, ))
        keys = curr.fetchall()
        conn.executemany("""
            DELETE FROM cache WHERE key=?;
        """, keys)
        for item in keys:
            key = item[0]
            del data[key]


class MemoryCache(object):

    def __init__(self, max_size=10000):
        self._max_size = int(max_size)
        self._queue = deque()
        self._cache = {}

    def __str__(self):
        return str(self._cache)

    def __len__(self):
        return len(self._cache)

    def put(self, key, val):
        if len(self._cache) >= self._max_size:
            ignore_key = self._queue.pop()
            del self._cache[ignore_key]
        self._queue.appendleft(key)
        self._cache[key] = val

    def get(self, key):
        val = self._cache.get(key)
        if val is None:
            return None
        self._queue.remove(key)
        self._queue.appendleft(key)
        return val

    def delete(self, key):
        if key not in self._cache:
            return
        self._queue.remove(key)
        del self._cache[key]


class Session(UserDict):

    def __init__(self, session_id):
        self.id = session_id
        self.data = {}

    def __str__(self):
        return "<Session Id=%s>" % self.id


class RequestHandler(object):

    default_headers = {
        "Content-Type": default_content_type
    }

    def __init__(self, app, rw, environ):
        self._rw = rw
        self._app = app
        self._environ = environ
        self._buffers = StringIO()
        self._headers_responsed = False
        self._response_headers = {}
        self._cookies = None
        self._status_code = 200
        self._get = parse_form(environ["QUERY_STRING"])
        content_type = environ.get("CONTENT_TYPE", "")
        content_type, params = cgi.parse_header(content_type)
        self._post = {}
        self._body = ""
        if content_type == 'application/x-www-form-urlencoded':
            post_content = environ.get("POST_CONTENT", "")
            self._post = parse_form(post_content)
        elif content_type == 'multipart/form-data':
            self._post = environ.pop(POSTS_HEADER_NAME, {})
        else:
            post_content = environ.get("POST_CONTENT", "")
            self._body = post_content
        self._session_id, self._session = self._get_session(environ)
        self._files = environ.pop(FILES_HEADER_NAME, {})
        if app.config.debug:
            log_debug(app.logger, "%s - \"%s %s %s\"" % (
                environ["REMOTE_HOST"],
                environ["SERVER_PROTOCOL"],
                environ["REQUEST_METHOD"],
                environ["PATH_INFO"]
            ))

    def _get_session(self, environ):
        app = self._app
        sessions = app.sessions
        cookie = environ.get("HTTP_COOKIE")
        cookie = SimpleCookie(cookie)
        morsel = cookie.get(default_sid)
        if morsel is not None:
            session_id = morsel.value
        else:
            session_id = self._new_session_id()
        session = sessions.get(session_id)
        if session is not None:
            return session_id, session
        session = Session(session_id)
        sessions.put(session_id, session)
        # New session
        return None, session

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while 1:
            token = "%s%s" % (urandom(24), time())
            if PY3:
                token = token.encode("utf-8")
            session_id = sha1(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

    def set_cookie(self, name, value, **options):
        cookies = self._cookies
        if not cookies:
            cookies = SimpleCookie()
        cookies[name] = value
        for key, value in options.items():
            if not value:
                continue
            cookies[name][key] = value
        self._cookies = cookies

    @property
    def config(self):
        return self._app.config

    @property
    def files(self):
        return self._files or {}

    @property
    def body(self):
        return self._body

    @property
    def json(self):
        body = self._body
        if not self._body:
            return {}
        content_type = self.content_type
        content_type, _ = cgi.parse_header(content_type)
        content_type = content_type.lower()
        if content_type not in ('application/json', 'application/json-rpc'):
            return {}
        return json.loads(body)

    @property
    def environ(self):
        return self._environ

    @property
    def params(self):
        return self._get

    @property
    def data(self):
        return self._post

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def request_method(self):
        return self.environ["REQUEST_METHOD"]
    method = request_method

    @property
    def server_protocol(self):
        return self.environ["SERVER_PROTOCOL"]

    @property
    def content_type(self):
        return self.environ.get("CONTENT_TYPE")

    @property
    def charset(self, default="UTF-8"):
        _, params = cgi.parse_header(self.content_type)
        return params.get("charset", default)

    @property
    def content_length(self):
        return int(self.environ.get("CONTENT_LENGTH") or -1)

    @property
    def path_info(self):
        return self.environ["PATH_INFO"]

    @property
    def query_string(self):
        return self.environ["QUERY_STRING"]

    @property
    def request_uri(self):
        environ = self.environ
        path_info = environ["PATH_INFO"]
        query_string = environ["QUERY_STRING"]
        if not query_string:
            return path_info
        return "?".join((path_info, query_string))

    @property
    def referer(self):
        return self.environ.get("HTTP_REFERER")

    @property
    def cookie(self):
        cookie_str = self.environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

    def start_response(self, status_code=200, headers=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        self._status_code = int(status_code)
        response_headers = self._response_headers
        response_headers["Server"] = server_info
        response_headers["Content-Type"] = "text/html;charset=utf-8"
        if headers is not None:
            for header in headers:
                if not isinstance(header, (list, tuple)):
                    if PY3:
                        header = header.encode("utf-8")
                    k, v = header.split(":")
                    k, v = k.strip(), v.strip()
                else:
                    k, v = header
                response_headers[k] = v
        if self.session_id is None:
            self.set_cookie(default_sid, self.session.id, path="/")
        self._headers_responsed = True

    def redirect(self, url=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        url = '/' if url is None else url
        response_headers = self._response_headers
        response_headers["Content-Type"] = "text/html;charset=utf-8"
        response_headers["Location"] = "http://%s%s" % (
            self._environ["HTTP_HOST"], url
        )
        status_code = 302
        status_text = http_status_codes[status_code]
        content = "%d %s" % (status_code, status_text)
        headers = response_headers.items()
        self.start_response(status_code, headers=headers)
        return content

    def _cast(self, s=None):
        response_headers = self._response_headers
        if not s:
            if "Content-Length" not in response_headers:
                response_headers["Content-Length"] = 0
            return []
        if isinstance(s, (tuple, list)) \
                and (is_unicode(s[0]) or is_bytes(s[0])):
            join_chr = s[0][:0]
            s = join_chr.join(s)
        if is_unicode(s):
            s = s.encode("utf-8")
        if is_bytes(s):
            if "Content-Length" not in response_headers:
                response_headers["Content-Length"] = len(s)
            return [s]
        try:
            iter_s = iter(s)
            first = next(iter_s)
            while not first:
                first = next(iter_s)
        except StopIteration:
            return self._cast()
        if is_bytes(first):
            new_iter_s = itertools.chain([first], iter_s)
        elif is_unicode(first):
            encoder = lambda item: str(item).encode("utf-8")
            new_iter_s = itertools.chain([first], iter_s)
            new_iter_s = imap(encoder, new_iter_s)
        else:
            raise TypeError("response type is not allowd: %s" % type(first))
        return new_iter_s

    def finish(self, content):
        rw = self._rw
        status_code = self._status_code
        status_text = http_status_codes[status_code]
        line = "HTTP/1.1 %d %s\r\n" % (status_code, status_text)
        if PY3:
            line = line.encode("utf-8")
        rw.write(line)
        headers = self._response_headers
        if not headers:
            headers = self.default_headers
        for header, value in headers.items():
            line = "%s: %s\r\n" % (header, value)
            if PY3:
                line = line.encode("utf-8")
            rw.write(line)
        if self._cookies:
            for c in self._cookies.values():
                line = "%s: %s\r\n" % ('Set-Cookie', c.OutputString())
                if PY3:
                    line = line.encode("utf-8")
                rw.write(line)
        rw.write("\r\n".encode("utf-8"))
        for _ in self._cast(content):
            rw.write(_)
        rw.close()

    def __del__(self):
        files = self._environ.get(FILES_HEADER_NAME)
        if not files:
            return
        for fp in files.values():
            fp.close()

    def _response(self, status_code, headers=None, content=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        status_code = int(status_code)
        status_text = http_status_codes[status_code]
        self.start_response(status_code, headers=headers)
        if content is None:
            content = DEFAULT_STATUS_MESSAGE % {
                "code": status_code,
                "message": status_text,
                "explain": status_text
            }
        return content

    def handler(self):
        app = self._app
        environ = self.environ
        path_info = environ["PATH_INFO"]
        path = startswith_dot_sub("/", path_info)
        path = double_slash_sub("/", path)
        if path != path_info:
            return self.redirect(path)
        base, name = path_split(path)
        if not name:
            name = default_page
        path = path_join(base, name)
        module = app.caches.get(path)
        if module is not None:
            try:
                return module.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    return self._response(500, content=content)
                return self._response(500)
        litefile = app.files.get(path)
        if litefile is not None:
            return litefile.handler(self)
        realpath = path_abspath(
            path_join(app.config.webroot, path.lstrip("/"))
        )
        if path_isdir(realpath):
            return self.redirect(path + "/")
        module = self._load_script(base, name)
        if module is not None and hasattr(module, "handler"):
            basepath, ext = path_splitext(path)
            if ext in (".mako", ):
                app.caches.put(basepath, module)
            else:
                app.caches.put(path, module)
            try:
                return module.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    return self._response(500, content=content)
                return self._response(500)
        try:
            litefile = self._load_static_file(base, name)
        except IOError:
            log_error(app.logger)
            return self._response(404)
        if litefile is not None:
            app.files.put(path, litefile)
            try:
                return litefile.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    return self._response(500, content=content)
                return self._response(500)
        path = app.config.not_found
        base, name = path_split(path)
        if not name:
            name = default_404
        try:
            litefile = self._load_static_file(base, name)
        except IOError:
            litefile = None
        if litefile is not None:
            app.files.put(path, litefile)
            litefile.status_code = 404
            try:
                return litefile.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    return self._response(500, content=content)
                return self._response(500)
        return self._response(404)

    def _load_static_file(self, base, name):
        app = self._app
        webroot = app.config.webroot
        realbase = path_realpath(
            path_abspath(path_join(webroot, base.lstrip('/')))
        )
        script_name, ext = path_splitext(name)
        realpath = path_join(realbase, name)
        if ext in suffixes or not path_isfile(realpath):
            return None
        with open(realpath, "rb") as fp:
            text = fp.read()
        return LiteFile(realpath, base, name, text)

    def _load_template(self, base, name):
        app = self._app
        webroot = app.config.webroot
        script_uri = path_join(base.lstrip("/"), name)
        path = path_join("/%s" % base.rstrip("/"), name)
        mylookup = TemplateLookup(directories=[webroot])
        def handler(mylookup, script_uri):
            def _handler(self):
                try:
                    template = mylookup.get_template(script_uri)
                    content = template.render(http=self)
                    headers = getattr(template.module, "headers", None)
                    if headers:
                        headers = "\r\n".join(
                            [":".join(h) for h in headers]
                        )
                    if not headers:
                        headers = [
                            ("Content-Type", "text/html;charset=utf-8")
                        ]
                    return self._response(
                        200, headers=headers, content=content
                    )
                except:
                    log_error(app.logger)
                    if app.config.debug:
                        content = render_error()
                        return self._response(500, content=content)
                    return self._response(500)
            return _handler
        module = new_module()
        module.handler = handler(mylookup, script_uri)
        return module

    def _load_script(self, base, name):
        app = self._app
        webroot = app.config.webroot
        realbase = path_realpath(
            path_abspath(path_join(webroot, base.lstrip("/")))
        )
        script_uri = path_join(base.lstrip("/"), name)
        script_name, ext = path_splitext(name)
        if ext in cgi_suffixes and \
                base.startswith(app.config.cgi_dir):
            runner = cgi_runners[ext]
            script_path = path_join(webroot, script_uri)
            if not path_isfile(script_path):
                def handler():
                    def _handler(self):
                        return self._response(404)
                    return _handler
                module = new_module()
                module.handler = handler()
                return module
            return self._load_cgi(runner, script_uri, webroot)
        tmplname = "%s.mako" % name
        tmplpath = path_join(realbase, tmplname)
        if path_exists(tmplpath):
            return self._load_template(base, tmplname)
        try:
            fp, pathname, description = find_module(name, [realbase])
        except ImportError:
            return None
        module_name = "litefs_%s" % uuid4().hex
        sys.dont_write_bytecode = True
        try:
            module = load_module(module_name, fp, pathname, description)
        except:
            log_error(app.logger)
            content = None
            if app.config.debug:
                content = render_error()
            def handler(content):
                def _handler(self):
                    return self._response(500, content=content)
                return _handler
            module = new_module()
            module.handler = handler(content)
            return module
        finally:
            sys.dont_write_bytecode = False
            if fp:
                fp.close()
        sys.modules.pop(module_name, None)
        return module

    def _load_cgi(self, runner, script_uri, webroot):
        app = self._app
        tmpf = NamedTemporaryFile("w+")
        try:
            p = Popen(
                [runner, script_uri],
                stdout=tmpf, stderr=PIPE, close_fds=True, cwd=webroot
            )
            stdout, stderr = p.communicate()
            returncode = p.returncode
            if 0 == returncode:
                log_debug(app.logger, "CGI script exited OK")
            else:
                log_error(app.logger,
                    "CGI script exit status %#x" % returncode
                )
            p.stderr.close()
            if stderr:
                log_debug(app.logger, stderr)
            tmpf.seek(0)
            if not stderr:
                stdout = tmpf.read()

            def handler(out, err):
                def _handler(self):
                    if out is not None:
                        return self._response(200, content=out)
                    else:
                        return self._response(500, content=err)
                return _handler

            module = new_module()
            module.handler = handler(stdout, stderr)
            return module
        finally:
            tmpf.close()


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
        data = ""
        if PY3:
            data = b""
        try:
            curr.parent.switch()
            data = self._sock.recv(len(b))
        except socket.error as e:
            # Fixed: Resource temporarily unavailable
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
            # Fixed: Resource temporarily unavailable
            if e.errno not in should_retry_error:
                raise
        finally:
            self.write_gr = None
            if self.read_gr is None:
                real_epoll.unregister(fileno)
            else:
                real_epoll.modify(fileno, EPOLLIN | EPOLLET)

    def close(self):
        if self.closed:
            return
        RawIOBase.close(self)
        try:
            self._sock.shutdown(socket.SHUT_RDWR)
        except socket.error as e:
            # The server might already have closed the connection
            if e.errno != ENOTCONN:
                raise
        self._sock.close()

    read_gr = write_gr = None


class Epoll(object):

    def __init__(self):
        self._epoll = select_epoll()
        self._servers = {}
        self._greenlets = {}

    def register(self, server_socket):
        servers = self._servers
        fileno = server_socket.fileno()
        servers[fileno] = server_socket
        self._epoll.register(fileno, EPOLLIN | EPOLLET)

    def close(self):
        for fileno, server_socket in self._servers.items():
            self._epoll.unregister(fileno)
            server_socket.server_close()
        self._epoll.close()

    def poll(self, poll_interval=.2):
        servers = self._servers
        greenlets = self._greenlets
        _poll = self._epoll.poll
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
        """Called if no new request arrives within self.timeout.

        Overridden by ForkingMixIn.
        """
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
        """Finish one request by instantiating RequestHandlerClass."""
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
            # explicitly shutdown.  socket.close() merely releases
            # the socket and waits for GC to perform the actual close.
            request.shutdown(socket.SHUT_WR)
        except OSError:
            pass  # some platforms may raise ENOTCONN here
        self.close_request(request)

    def close_request(self, request):
        request.close()

    def handle_error(self, request, client_address):
        import traceback
        traceback.print_exc()  # XXX But this goes to stderr!

    def server_forever(self, poll_interval=.1):
        if not self._started:
            epoll.register(self)
        mainloop(poll_interval=poll_interval)

    def start(self):
        if not self._started:
            epoll.register(self)

    def shutdown(self):
        if self._started:
            epoll.unregister(self)


class HTTPServer(TCPServer):

    allow_reuse_address = 1

    def server_bind(self):
        """Override server_bind to store the server name."""
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
        # Set up base environment
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


class Litefs(object):

    def __init__(self, **kwargs):
        self.config = config = make_config(**kwargs)
        level = logging.DEBUG if config.debug else logging.INFO
        self.logger = make_logger(__name__, log=config.log, level=level)
        self.host = host = config.host
        self.port = port = config.port
        self.server = HTTPServer((host, port), self.handler)
        self.sessions = MemoryCache(max_size=1000000)
        self.caches = TreeCache()
        self.files = TreeCache()
        now = datetime.now().strftime("%B %d, %Y - %X")
        sys.stdout.write((
            "Litefs %s - %s\n"
            "Starting server at http://%s:%d/\n"
            "Quit the server with CONTROL-C.\n"
        ) % (__version__, now, host, port))

    def handler(self, request, environ, server):
        raw = SocketIO(server, request)
        rw = BufferedRWPair(raw, raw, DEFAULT_BUFFER_SIZE)
        request_handler = RequestHandler(self, rw, environ)
        result = request_handler.handler()
        return request_handler.finish(result)

    def run(self, poll_interval=.2):
        observer = Observer()
        event_handler = FileEventHandler(self)
        observer.schedule(event_handler, self.config.webroot, True)
        observer.start()
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
        required=False, default=default_404,
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


def mainloop(poll_interval=.1):
    try:
        epoll.poll(poll_interval=poll_interval)
    except KeyboardInterrupt:
        pass
    finally:
        epoll.close()

server_forever = mainloop


def test_server():
    args = _cmd_args(sys.argv)
    kwargs = vars(args)
    litefs = Litefs(**kwargs)
    litefs.run(poll_interval=.1)

epoll = Epoll()

if "__main__" == __name__:
    test_server()
