#!/usr/bin/env python
#-*- coding: utf-8 -*-

__doc__ = '''\
Build a web server framework using Python. Litefs was developed to imple\
ment a server framework that can quickly, securely, and flexibly build Web \
projects. Litefs is a high-performance HTTP server. Litefs has the characte\
ristics of high stability, rich functions, and low system consumption.

Author: leafcoder
Email: leafcoder@gmail.com

Copyright (c) 2017, Leafcoder.
License: MIT (see LICENSE for details)
'''

__version__ = '0.3.0'
__author__  = 'Leafcoder'
__license__ = 'MIT'

import argparse
import logging
import re
import sys
from collections import deque, Iterable
from datetime import datetime
from errno import ENOTCONN, EMFILE, EWOULDBLOCK, EAGAIN, EPIPE
from functools import partial
from greenlet import greenlet, getcurrent, GreenletExit
from gzip import GzipFile
from hashlib import sha1
from imp import find_module, load_module, new_module as imp_new_module
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
from sqlite3 import connect as sqlite3_connect
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile, TemporaryFile
from time import time, strftime, gmtime
from uuid import uuid4
from watchdog.events import *
from watchdog.observers import Observer
from weakref import proxy as weakref_proxy
from zlib import compress as zlib_compress
from io import RawIOBase, BufferedRWPair, DEFAULT_BUFFER_SIZE

PY3 = sys.version_info.major > 2

if PY3:
    # Import modules in py3
    import socket
    from http.client import responses as http_status_codes
    from http.cookies import SimpleCookie
    from io import BytesIO as StringIO
    from urllib.parse import splitport, unquote_plus
    from collections import UserDict
    def is_unicode(s):
        return isinstance(s, str)
    def is_bytes(s):
        return isinstance(s, bytes)
else:
    # Import modules in py2
    import _socket as socket
    from Cookie import SimpleCookie
    from cStringIO import StringIO
    from httplib import responses as http_status_codes
    from urllib import splitport, unquote_plus
    from UserDict import UserDict
    def is_unicode(s):
        return isinstance(s, unicode)
    def is_bytes(s):
        return isinstance(s, basestring)

server_name = 'litefs'
server_software = 'litefs %s' % __version__

default_404 = 'not_found'
default_sid = '%s.sid' % server_name
default_content_type = 'text/plain'

EOFS = ('', '\n', '\r\n')
FILES_HEADER_NAME = 'litefs.files'
date_format = '%Y/%m/%d %H:%M:%S'
should_retry_error = (EWOULDBLOCK, EAGAIN)
double_slash_sub = re.compile(r'\/{2,}').sub
startswith_dot_sub = re.compile(r'\/\.+').sub
suffixes = ('.py', '.pyc', '.pyo', '.so', '.mako')
cgi_suffixes = ('.pl', '.py', '.pyc', '.pyo', '.php')
form_dict_match = re.compile(r'(.+)\[([^\[\]]+)\]').match
server_info = 'litefs/%s python/%s' % (__version__, sys.version.split()[0])
cgi_runners = {
    '.pl' : '/usr/bin/perl',
    '.py' : '/usr/bin/python',
    '.pyc': '/usr/bin/python',
    '.pyo': '/usr/bin/python',
    '.php': '/usr/bin/php',
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
        message = 'error occured'
    logger.error(message, exc_info=True)

def log_info(logger, message=None):
    if message is None:
        message = 'info'
    logger.info(message)

def log_debug(logger, message=None):
    if message is None:
        message = 'debug'
    logger.debug(message)

class HttpError(Exception):
    pass

def render_error():
    return exceptions.html_error_template().render()

def gmt_date(timestamp=None):
    if timestamp is None:
        timestamp = time()
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(timestamp))

def new_module(**kwargs):
    '''创建新模块

    新创建的模块不会加入到 sys.path 中，并导入自定义属性。
    '''
    module_name = ''.join((server_name, uuid4().hex))
    module = imp_new_module(module_name)
    module.__dict__.update(kwargs)
    return module

def make_config(**kwargs):
    args = _cmd_args(sys.argv)
    default_config = {}
    default_config.update(kwargs)
    default_config.update(vars(args))
    config = new_module(**default_config)
    config.webroot = path_abspath(config.webroot)
    return config

def make_logger(name, log=None, level=logging.DEBUG):
    '''创建日志对象

    输出 HTTP 访问日志和错误异常。
    '''
    logger = logging.getLogger(name)
    fmt = logging.Formatter(
        ('%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message'
         ')s'),
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
    """Read HTTP headers"""
    headers = {}
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    if PY3: s = s.decode('utf-8')
    while True:
        if s in EOFS:
            break
        k, v = s.split(':', 1)
        k, v = k.lower().strip(), v.strip()
        headers[k] = v
        s = rw.readline(DEFAULT_BUFFER_SIZE)
        if PY3: s = s.decode('utf-8')
    return headers

def make_environ(app, rw, client_address):
    environ = {}
    environ['SERVER_NAME'] = server_name
    environ['SERVER_SOFTWARE'] = server_software
    environ['SERVER_PORT'] = app.port
    environ['REMOTE_ADDR'] = client_address
    environ['REMOTE_HOST'] = client_address[0]
    environ['REMOTE_PORT'] = client_address[1]
    # Read first line
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    if PY3: s = s.decode('utf-8')
    if not s:
        # 注意：读出来为空字符串时，代表着服务器在等待读
        raise HttpError('invalid http headers')
    request_method, path_info, protocol = s.strip().split()
    if '?' in path_info:
        path_info, query_string = path_info.split('?', 1)
    else:
        path_info, query_string = path_info, ''
    path_info = unquote_plus(path_info)
    base_uri, script_name = path_info.split('/', 1)
    if '' == script_name:
        script_name = app.config.default_page
    environ['REQUEST_METHOD'] = request_method
    environ['QUERY_STRING'] = unquote_plus(query_string)
    environ['SERVER_PROTOCOL'] = protocol
    environ['SCRIPT_NAME'] = script_name
    environ['PATH_INFO'] = path_info
    headers = make_headers(rw)
    length = headers.get('content-length')
    if length:
        environ['CONTENT_LENGTH'] = length = int(length)
    content_type = headers.get('content-type')
    if content_type:
        environ['CONTENT_TYPE'] = content_type
    else:
        environ['CONTENT_TYPE'] = default_content_type
    for k, v in headers.items():
        k = k.replace('-', '_').upper()
        # skip content_length, content_type, etc.
        if k in environ:
            continue
        k = 'HTTP_%s' % k
        if k in environ:
            environ[k] += ',%s' % v # comma-separate multiple headers
        else:
            environ[k] = v
    if not length:
        return environ
    content_type = environ.get('CONTENT_TYPE', '')
    if content_type.startswith('multipart/form-data'):
        environ[FILES_HEADER_NAME] \
            = parse_multipart(rw, content_type, length)
    else:
        environ['POST_CONTENT'] = post_content = rw.read(int(length))
        if PY3:
            environ['POST_CONTENT'] \
                = unquote_plus(post_content.decode('utf-8'))
        environ['CONTENT_LENGTH'] = len(environ['POST_CONTENT'])
    for k in ('CONTENT_LENGTH', 'HTTP_USER_AGENT', 'HTTP_COOKIE',
              'HTTP_REFERER'):
        environ.setdefault(k, '')
    return environ

def parse_multipart(rw, content_type, length):
    boundary = content_type.split('=')[1].strip()
    begin_boundary = ('--%s' % boundary)
    end_boundary = ('--%s--' % boundary)
    files = {}
    s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
    if PY3: s = s.decode('utf-8')
    while True:
        if s.strip() != begin_boundary:
            assert s.strip() == end_boundary
            break
        headers = {}
        s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
        if PY3: s = s.decode('utf-8')
        while s:
            k, v = s.split(':', 1)
            headers[k.strip().upper()] = v.strip()
            s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
            if PY3: s = s.decode('utf-8')
        disposition = headers['CONTENT-DISPOSITION']
        h, m, t = disposition.split(';')
        name = m.split('=')[1].strip()
        if length <= 5242880: # <= 5M file save in memory
            fp = StringIO()
        else:
            fp = TemporaryFile(mode='w+b')
        s = rw.readline(DEFAULT_BUFFER_SIZE)
        if PY3: s = s.decode('utf-8')
        while s.strip() != begin_boundary \
                and s.strip() != end_boundary:
            fp.write(s.encode('utf-8'))
            s = rw.readline(DEFAULT_BUFFER_SIZE)
            if PY3: s = s.decode('utf-8')
        fp.seek(0)
        files[name[1:-1]] = fp
    return files

def parse_form(form, qstr):
    qstr = unquote_plus(qstr)
    for s in qstr.split('&'):
        if not s:
            continue
        kv = s.split('=', 1)
        if 2 == len(kv):
            k, v = kv
        else:
            k, v = kv[0], ''
        k, v = unquote_plus(k), unquote_plus(v)
        if k.endswith('[]'):
            k = k[:-2]
            if k in form:
                result = form[k]
                if isinstance(result, dict):
                    raise ValueError('invalid form data %s' % qstr)
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
                    raise ValueError('invalid form data %s' % qstr)
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
                    raise ValueError('invalid form data %s' % qstr)
                if prefix in result:
                    result[prefix] = [result[prefix], v]
                else:
                    result[prefix] = v
            else:
                form[key] = { prefix: v }

def make_form(environ):
    query_string = environ['QUERY_STRING']
    form = {}
    parse_form(form, query_string)
    post_content = environ.get('POST_CONTENT')
    if post_content:
        parse_form(form, post_content)
    return form

class FileEventHandler(FileSystemEventHandler):

    def __init__(self, app):
        FileSystemEventHandler.__init__(self)
        self._app = weakref_proxy(app)

    def on_moved(self, event):
        src_path = event.src_path
        dest_path = event.dest_path
        webroot = self._app.config.webroot
        if webroot == src_path and event.is_directory:
            return
        if not src_path.startswith(webroot+'/'):
            return
        if webroot == dest_path and event.is_directory:
            return
        if not dest_path.startswith(webroot+'/'):
            return
        log_info(self._app.logger, '%s has been moved to %s' \
            % (src_path, dest_path))
        src_path  = '/%s' % src_path [len(webroot):].strip('/')
        dest_path = '/%s' % dest_path[len(webroot):].strip('/')
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
        if not src_path.startswith(webroot+'/'):
            return
        log_info(self._app.logger, '%s has been modified' % src_path)
        src_path = '/%s' % src_path[len(webroot):].strip('/')
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

    def __init__(self, path, base, name, text):
        self.path = path
        self.text = text
        self.etag = etag = sha1(text).hexdigest()
        self.zlib_text = zlib_text = zlib_compress(text, 9)[2:-4]
        self.zlib_etag = sha1(zlib_text).hexdigest()
        stream = StringIO()
        with GzipFile(fileobj=stream, mode="wb") as f:
            f.write(text)
        self.gzip_text = gzip_text = stream.getvalue()
        self.gzip_etag = sha1(gzip_text).hexdigest()
        self.last_modified = gmt_date(stat(path).st_mtime)
        mimetype, coding = guess_type(name)
        headers = [('Content-Type', 'text/html;charset=utf-8')]
        if mimetype is not None:
            headers = [('Content-Type', '%s;charset=utf-8' % mimetype)]
        headers.append(('Last-Modified', self.last_modified))
        headers.append(('Connection', 'close'))
        self.headers = headers

    def handler(self, request):
        environ = request.environ
        if_modified_since = environ.get('HTTP_IF_MODIFIED_SINCE')
        if if_modified_since == self.last_modified:
            result = request._response(304)
            return request.finish(result)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        accept_encodings = environ.get(
            'HTTP_ACCEPT_ENCODING', '').split(',')
        accept_encodings = [s.strip().lower() for s in accept_encodings]
        headers = list(self.headers)
        if 'gzip' in accept_encodings:
            if if_none_match == self.gzip_etag:
                result = request._response(304)
                return request.finish(result)
            headers.append(('Etag', self.gzip_etag))
            headers.append(('Content-Encoding', 'gzip'))
            text = self.gzip_text
        elif 'deflate' in accept_encodings:
            if if_none_match == self.zlib_etag:
                result = request._response(304)
                return request.finish(result)
            headers.append(('Etag', self.zlib_etag))
            headers.append(('Content-Encoding', 'deflate'))
            text = self.zlib_text
        else:
            if if_none_match == self.etag:
                result = request._response(304)
                return request.finish(result)
            headers.append(('Etag', self.etag))
            text = self.text
        headers.append(('Content-Length', '%d' % len(text)))
        result = request._response(200, headers=headers, content=text)
        return request.finish(result)

class TreeCache(object):

    def __init__(self, clean_period=60, expiration_time=3600):
        self.data = {}
        self.clean_time = time()
        self.clean_period = clean_period
        self.expiration_time = expiration_time
        self.conn = sqlite3_connect(':memory:', check_same_thread=False)
        self.conn.text_factory = str
        self.conn.executescript('''
            CREATE TABLE IF NOT EXISTS cache (
                key VARCHAR PRIMARY KEY,
                timestamp INTEGER
            );
            CREATE INDEX idx_cache ON cache (key);
        ''')

    def __len__(self):
        return len(self.data)

    def put(self, key, val):
        conn = self.conn
        data = self.data
        if self.clean_time + self.clean_period < time():
            self.auto_clean()
        timestamp = int(time())
        if key not in data:
            conn.execute('''
                INSERT INTO cache (key, timestamp) VALUES (?, ?);
            ''', (key, timestamp))
        else:
            conn.execute('''
                UPDATE cache SET timestamp=? WHERE key=?;
            ''', (timestamp, key))
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
        curr = conn.execute('''\
            SELECT key FROM cache WHERE key=? OR key LIKE ?;
        ''', (key, key + '/%'))
        keys = curr.fetchall()
        conn.executemany('''\
            DELETE FROM cache WHERE key=?;
        ''', keys)
        for item in keys:
            key = item[0]
            del data[key]

    def auto_clean(self):
        conn = self.conn
        data = self.data
        last_expiration_time = int(time() - self.expiration_time)
        curr = conn.execute('''
            SELECT key FROM cache WHERE timestamp < ?;
        ''', (last_expiration_time, ))
        keys = curr.fetchall()
        conn.executemany('''
            DELETE FROM cache WHERE key=?;
        ''', keys)
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
        return '<Session Id=%s>' % self.id

class HttpRequest(object):

    def __init__(self, app, rw, environ, client_address):
        self._rw = rw
        self._app = app
        self._environ = environ
        self._client_address = client_address
        self._buffers = StringIO()
        self._headers_responsed = False
        self._form = make_form(environ)
        self._session_id, self._session = self._get_session(environ)
        self._files = environ.pop(FILES_HEADER_NAME, None)
        if app.config.debug:
            log_debug(app.logger,
                '%s - "%s %s %s"' % (
                    environ['REMOTE_HOST'],
                    environ['SERVER_PROTOCOL'],
                    environ['REQUEST_METHOD'],
                    environ['PATH_INFO']
                )
            )

    def _get_session(self, environ):
        app = self._app
        sessions = app.sessions
        cookie = environ.get('HTTP_COOKIE')
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
        return session_id, session

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while 1:
            token = '%s%s' % (urandom(24), time())
            if PY3:
                token = token.encode('utf-8')
            session_id = sha1(token).hexdigest()
            if PY3:
                session_id = session_id.encode('utf-8')
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

    @property
    def config(self):
        return self._app.config

    @property
    def client_address(self):
        return self._client_address

    @property
    def files(self):
        return self._files or {}

    @property
    def environ(self):
        return self._environ

    @property
    def form(self):
        return self._form

    @property
    def session_id(self):
        return self._session_id

    @property
    def session(self):
        return self._session

    @property
    def request_method(self):
        return self.environ['REQUEST_METHOD']

    @property
    def server_protocol(self):
        return self.environ['SERVER_PROTOCOL']

    @property
    def content_type(self):
        return self.environ.get('CONTENT_TYPE')

    @property
    def path_info(self):
        return self.environ['PATH_INFO']

    @property
    def query_string(self):
        return self.environ['QUERY_STRING']

    @property
    def request_uri(self):
        environ = self.environ
        path_info = environ['PATH_INFO']
        query_string = environ['QUERY_STRING']
        if not query_string:
            return path_info
        return '?'.join((path_info, query_string))

    @property
    def referer(self):
        return self.environ.get('HTTP_REFERER')

    @property
    def cookie(self):
        cookie_str = self.environ.get('HTTP_COOKIE', '')
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

    def start_response(self, status_code=200, headers=None):
        buffers = self._buffers
        if self._headers_responsed:
            raise ValueError('Http headers already responsed.')
        response_headers = {}
        response_headers['Server'] = server_info
        response_headers['Content-Type'] = 'text/html;charset=utf-8'
        status_code = int(status_code)
        status_text = http_status_codes[status_code]
        line = 'HTTP/1.1 %d %s\r\n' % (status_code, status_text)
        if PY3:
            line = line.encode('utf-8')
        buffers.write(line)
        header_names = []
        if headers is not None:
            for header in headers:
                if not isinstance(header, (list, tuple)):
                    if PY3:
                        header = header.encode('utf-8')
                    k, v = header.split(':')
                    k, v = k.strip(), v.strip()
                    header = (k, v)
                header_names.append(header[0])
                line = '%s: %s\r\n' % header
                if PY3:
                    line = line.encode('utf-8')
                buffers.write(line)
        for name, text in response_headers.items():
            if name in header_names:
                continue
            line = '%s: %s\r\n' % (name, text)
            if PY3:
                line = line.encode('utf-8')
            buffers.write(line)
        if self.session_id is None:
            cookie = SimpleCookie()
            cookie[default_sid] = self.session.id
            cookie[default_sid]['path'] = '/'
            line = '%s\r\n' % cookie.output()
            if PY3:
                line = line.encode('utf-8')
            buffers.write(line)
        if PY3:
            buffers.write(b'\r\n')
        else:
            buffers.write('\r\n')
        self._headers_responsed = True

    def redirect(self, url=None):
        if self._headers_responsed:
            raise ValueError('Http headers already responsed.')
        url = '/' if url is None else url
        response_headers = {}
        response_headers['Content-Type'] = 'text/html;charset=utf-8'
        response_headers['Location'] = 'http://%s%s' % (
            self._environ['HTTP_HOST'], url
        )
        status_code = 302
        status_text = http_status_codes[status_code]
        content = '%d %s' % (status_code, status_text)
        headers = response_headers.items()
        self.start_response(status_code, headers=headers)
        return content

    def finish(self, content):
        rw = self._rw
        if not self._headers_responsed:
            self.start_response(200)
        rw.write(self._buffers.getvalue())
        if is_unicode(content):
            rw.write(content.encode('utf-8'))
        elif is_bytes(content):
            rw.write(content)
        elif isinstance(content, (list, tuple, Iterable)):
            for s in content:
                if is_unicode(s):
                    rw.write(s.encode('utf-8'))
                elif is_bytes(s):
                    rw.write(s)
                else:
                    s = str(s)
                    if PY3:
                        s = s.encode('utf-8')
                    rw.write(s)
        else:
            content = str(content)
            if PY3:
                content = content.encode('utf-8')
            rw.write(content)
        try:
            rw.close()
        except:
            pass

    def __del__(self):
        files = self._environ.get(FILES_HEADER_NAME)
        if not files:
            return
        for fp in files.values():
            fp.close()

    def _response(self, status_code, headers=None, content=None):
        if self._headers_responsed:
            raise ValueError('Http headers already responsed.')
        status_code = int(status_code)
        status_text = http_status_codes[status_code]
        self.start_response(status_code, headers=headers)
        if content is None:
            content = DEFAULT_STATUS_MESSAGE % {
                'code': status_code,
                'message': status_text,
                'explain': status_text
            }
        return content

    def handler(self):
        app = self._app
        environ = self.environ
        path_info = environ['PATH_INFO']
        path = startswith_dot_sub('/', path_info)
        path = double_slash_sub('/', path)
        if path != path_info:
            result = self.redirect(path)
            try:
                return self.finish(result)
            except:
                content = render_error()
                result = self._response(500, content=content)
                return self.finish(result)
        base, name = path_split(path)
        if not name:
            name = app.config.default_page
        path = path_join(base, name)
        module = app.caches.get(path)
        if module is not None:
            try:
                result = module.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    result = self._response(500, content=content)
                    return self.finish(result)
                result = self._response(500)
                return self.finish(result)
            else:
                try:
                    return self.finish(result)
                except:
                    result = render_error()
                    return self.finish(result)
        litefile = app.files.get(path)
        if litefile is not None:
            return litefile.handler(self)
        realpath = path_abspath(
            path_join(app.config.webroot, path.lstrip('/'))
        )
        if path_isdir(realpath):
            result = self.redirect(path + '/')
            return self.finish(result)
        module = self._load_script(base, name)
        if module is not None and hasattr(module, 'handler'):
            basepath, ext = path_splitext(path)
            if ext in ('.mako', ):
                app.caches.put(basepath, module)
            else:
                app.caches.put(path, module)
            try:
                result = module.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    result = self._response(500, content=content)
                    return self.finish(result)
                result = self._response(500)
                return self.finish(result)
            else:
                try:
                    return self.finish(result)
                except:
                    result = render_error()
                    return self.finish(result)
        try:
            litefile = self._load_static_file(base, name)
        except IOError:
            log_error(app.logger)
            result = self._response(404)
            return self.finish(result)
        if litefile is not None:
            app.files.put(path, litefile)
            try:
                return litefile.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    result = self._response(500, content=content)
                    return self.finish(result)
                result = self._response(500)
                return self.finish(result)
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
            try:
                return litefile.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    result = self._response(500, content=content)
                    return self.finish(result)
                result = self._response(500)
                return self.finish(result)
        result = self._response(404)
        return self.finish(result)

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
        with open(realpath, 'rb') as fp:
            text = fp.read()
        return LiteFile(realpath, base, name, text)

    def _load_template(self, base, name):
        app = self._app
        webroot = app.config.webroot
        script_uri = path_join(base.lstrip('/'), name)
        path = path_join('/%s' % base.rstrip('/'), name)
        mylookup = TemplateLookup(directories=[webroot])
        def handler(mylookup, script_uri):
            def _handler(self):
                try:
                    template = mylookup.get_template(script_uri)
                    content = template.render(http=self)
                    headers = getattr(template.module, 'headers', None)
                    if headers:
                        headers = '\r\n'.join(
                            [':'.join(h) for h in headers]
                        )
                    if not headers:
                        headers = [
                            ('Content-Type', 'text/html;charset=utf-8')
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
            path_abspath(path_join(webroot, base.lstrip('/')))
        )
        script_uri = path_join(base.lstrip('/'), name)
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
        tmplname = '%s.mako' % name
        tmplpath = path_join(realbase, tmplname)
        if path_exists(tmplpath):
            return self._load_template(base, tmplname)
        try:
            fp, pathname, description = find_module(name, [realbase])
        except ImportError:
            return None
        module_name = 'litefs_%s' % uuid4().hex
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
        tmpf = NamedTemporaryFile('w+')
        try:
            p = Popen(
                [runner, script_uri],
                stdout=tmpf, stderr=PIPE, close_fds=True, cwd=webroot
            )
            stdout, stderr = p.communicate()
            returncode = p.returncode
            if 0 == returncode:
                log_debug(app.logger, 'CGI script exited OK')
            else:
                log_error(app.logger,
                    'CGI script exit status %#x' % returncode
                )
            p.stderr.close()
            if stderr:
                log_debug(app.logger, stderr)
            tmpf.seek(0)
            if not stderr:
                stdout = tmpf.read()
            def handler(stdout, stderr):
                def _handler(self):
                    if stdout is not None:
                        return self._response(200, content=stdout)
                    else:
                        return self._response(500, content=stderr)
                return _handler
            module = new_module()
            module.handler = handler(stdout, stderr)
            return module
        finally:
            tmpf.close()

class RawIO(RawIOBase):

    def __init__(self, app, sock):
        RawIOBase.__init__(self)
        self._fileno = sock.fileno()
        self._sock = sock
        self._app = app

    def fileno(self):
        return self._fileno

    def readable(self):
        return True

    def writable(self):
        return True

    def readinto(self, b):
        epoll = self._app.epoll
        fileno = self._fileno
        curr = getcurrent()
        self.read_gr = curr
        if self.write_gr is None:
            epoll.register(fileno, EPOLLIN | EPOLLET)
        else:
            epoll.modify(fileno, EPOLLIN | EPOLLOUT | EPOLLET)
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
                epoll.unregister(fileno)
            else:
                epoll.modify(fileno, EPOLLOUT | EPOLLET)
        n = len(data)
        try:
            b[:n] = data
        except TypeError as err:
            import array
            if not isinstance(b, array.array):
                raise err
            b[:n] = array.array(b'b', data)
        return n

    def write(self, data):
        epoll = self._app.epoll
        fileno = self._fileno
        curr = getcurrent()
        self.write_gr = curr
        if self.read_gr is None:
            epoll.register(fileno, EPOLLOUT | EPOLLET)
        else:
            epoll.modify(fileno, EPOLLIN | EPOLLOUT | EPOLLET)
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
                epoll.unregister(fileno)
            else:
                epoll.modify(fileno, EPOLLIN | EPOLLET)

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

class Litefs(object):

    def __init__(self, **kwargs):
        self.config = config = make_config(**kwargs)
        level = logging.DEBUG if config.debug else logging.INFO
        self.logger = make_logger(__name__, log=config.log, level=level)
        self.host = host = config.host
        self.port = port = config.port
        self.server_address = '%s:%d' % (host, port)
        self.socket = socket = make_server(
            host, port, request_size=config.listen
        )
        self.fileno = fileno = socket.fileno()
        self.sessions = MemoryCache(max_size=1000000)
        self.caches = TreeCache()
        self.files  = TreeCache()
        self.epoll = select_epoll()
        self.epoll.register(fileno, EPOLLIN | EPOLLET)
        self.grs = {}
        now = datetime.now().strftime('%B %d, %Y - %X')
        sys.stdout.write((
            "Litefs %s - %s\n"
            "Starting server at http://%s:%d/\n"
            "Quit the server with CONTROL-C.\n"
        ) % (__version__, now, host, port))

    def handle_accept(self):
        while True:
            try:
                sock, client_address = self.socket.accept()
            except socket.error as e:
                errno = e.args[0]
                if EAGAIN == errno or EWOULDBLOCK == errno:
                    return
                raise
            sock.setblocking(0)
            fileno = sock.fileno()
            raw = RawIO(self, sock)
            self.grs[fileno] = gr = greenlet(
                partial(self.handle_io, raw, client_address)
            )
            gr.switch()

    def handle_io(self, raw, client_address):
        try:
            rw = BufferedRWPair(raw, raw, DEFAULT_BUFFER_SIZE)
            environ = make_environ(self, rw, client_address)
            request = HttpRequest(self, rw, environ, client_address)
            request.handler()
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
                self.grs.pop(fileno, None)
            try:
                raw.close()
            except:
                pass

    def poll(self, timeout=.2):
        while True:
            events = self.epoll.poll(timeout)
            for fileno, event in events:
                if fileno == self.fileno:
                    try:
                        self.handle_accept()
                    except KeyboardInterrupt:
                        break
                    except socket.error as e:
                        if e.errno == EMFILE:
                            raise
                        log_error(self.logger)
                    except:
                        log_error(self.logger)
                elif (event & EPOLLIN) or (event & EPOLLOUT):
                    try:
                        self.grs[fileno].switch()
                    except KeyboardInterrupt:
                        break
                    except:
                        log_error(self.logger)
                elif event & (EPOLLHUP | EPOLLERR):
                    try:
                        self.grs[fileno].throw()
                    except KeyboardInterrupt:
                        break
                    except:
                        log_error(self.logger)

    def run(self, timeout=.2):
        observer = Observer()
        event_handler = FileEventHandler(self)
        observer.schedule(event_handler, self.config.webroot, True)
        observer.start()
        try:
            self.poll(timeout=timeout)
        except KeyboardInterrupt:
            pass
        except:
            log_error(self.logger)
        finally:
            observer.stop()
            observer.join()
            self.epoll.unregister(self.fileno)
            self.epoll.close()
            self.socket.close()

def _cmd_args(args):
    parser = argparse.ArgumentParser(args[0], description=__doc__)
    parser.add_argument('--host', action='store', dest='host',
        required=False, default='localhost')
    parser.add_argument('--port', action='store', dest='port', type=int,
        required=False, default=9090)
    parser.add_argument('--webroot', action='store', dest='webroot',
        required=False, default='./site')
    parser.add_argument('--debug', action='store', dest='debug',
        required=False, default=False)
    parser.add_argument('--not-found', action='store', dest="not_found",
        required=False, default=default_404)
    parser.add_argument('--default-page', action='store',
        dest='default_page', required=False, default='index.html')
    parser.add_argument('--cgi-dir', action='store', dest='cgi_dir',
        required=False, default='/cgi-bin')
    parser.add_argument('--log', action='store', dest='log',
        required=False)
    parser.add_argument('--listen', action='store', dest='listen', type=int,
        required=False, default=1024)
    args = parser.parse_args(args and args[1:])
    return args

def test_server():
    litefs = Litefs()
    litefs.run(timeout=2.)

if '__main__' == __name__:
    test_server()
