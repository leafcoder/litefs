#!/usr/bin/env python
#-*- coding: utf-8 -*-

'''使用 Python 从零开始构建一个 Web 服务器框架。 开发 Litefs 的是为了实现一个能快速、安\
全、灵活的构建 Web 项目的服务器框架。 Litefs 是一个高性能的 HTTP 服务器。Litefs 具有高\
稳定性、丰富的功能、系统消耗低的特点。

Name: leafcoder
Email: leafcoder@gmail.com

Copyright (c) 2017, Leafcoder.
License: MIT (see LICENSE for details)
'''

__version__ = '0.2.5'
__author__  = 'Leafcoder'
__license__ = 'MIT'

import logging
import re
import sys
import _socket as socket
from collections import deque, Iterable
from Cookie import SimpleCookie
from cStringIO import StringIO
from errno import ENOTCONN, EMFILE, EWOULDBLOCK, EAGAIN, EPIPE
from functools import partial
from greenlet import greenlet, getcurrent, GreenletExit
from gzip import GzipFile
from hashlib import sha1
from httplib import responses as http_status_codes
from imp import find_module, load_module, new_module as imp_new_module
from mako import exceptions
from mako.lookup import TemplateLookup
from mimetypes import guess_type
from os import urandom, stat
from platform import platform
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
from urllib import splitport, unquote_plus
from UserDict import UserDict
from uuid import uuid4
from watchdog.events import *
from watchdog.observers import Observer
from weakref import proxy as weakref_proxy
from zlib import compress as zlib_compress
from io import RawIOBase, BufferedRWPair, DEFAULT_BUFFER_SIZE

default_404 = '404'
default_port = 9090
default_host = 'localhost'
default_prefix = 'litefs'
default_page = 'index.html'
default_webroot = './site'
default_cgi_dir = '/cgi-bin'
default_request_size = 10240
default_litefs_sid = '%s.sid' % default_prefix

server_name = 'litefs %s' % __version__
EOFS = ('', '\n', '\r\n')
FILES_HEADER_NAME = 'litefs.files'
date_format = '%Y/%m/%d %H:%M:%S'
should_retry_error = (EWOULDBLOCK, EAGAIN)
double_slash_sub = re.compile(r'\/{2,}').sub
startswith_dot_sub = re.compile(r'\/\.+').sub
suffixes = ('.py', '.pyc', '.pyo', '.so', '.mako')
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

class HttpError(Exception):
    pass

def gmt_date(timestamp=None):
    if timestamp is None:
        timestamp = time()
    return strftime('%a, %d %b %Y %H:%M:%S GMT', gmtime(timestamp))

def new_module(**kwargs):
    '''创建新模块

    新创建的模块不会加入到 sys.path 中，并导入自定义属性。
    '''
    mod_name = ''.join((default_prefix, uuid4().hex))
    mod = imp_new_module(mod_name)
    mod.__dict__.update(kwargs)
    return mod

def make_config(**kwargs):
    default_config = {
        'address'     : '%s:%d' % (default_host, default_port),
        'webroot'     : default_webroot,
        'cgi_dir'     : default_cgi_dir,
        'default_page': default_page,
        'not_found'   : default_404,
        'debug'       : False,
        'request_size': default_request_size
    }
    default_config.update(kwargs)
    config = new_module(**default_config)
    config.webroot = path_abspath(config.webroot)
    return config

def make_logger(name, level=logging.DEBUG):
    '''创建日志对象

    输出 HTTP 访问日志和错误异常。
    '''
    logger = logging.getLogger(name)
    logger.setLevel(level)
    handler = logging.StreamHandler()
    fmt = logging.Formatter(
        '%(asctime)s - %(message)s', datefmt=date_format
    )
    handler.setFormatter(fmt)
    logger.addHandler(handler)
    return logger

def log_error(logger, message=None):
    if message is None:
        message = 'error occured'
    logger.error(message, exc_info=True)

def log_debug(logger, message=None):
    if message is None:
        message = 'debug'
    logger.debug(message)

def make_server(address, request_size=-1):
    host, port = splitport(address)
    port = 80 if port is None else int(port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((host, port))
    if -1 == request_size:
        request_size = default_request_size
    sock.listen(request_size)
    sock.setblocking(0)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return {
        'address': '%s:%d' % (host, port),
        'fileno' : sock.fileno(),
        'socket' : sock,
        'host'   : host,
        'port'   : port
    }

def make_environ(app, rw, address):
    environ = {}
    environ['SERVER_NAME'] = server_name
    environ['SERVER_PORT'] = int(app.server_info['port'])
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    if not s:
        # 注意：读出来为空字符串时，代表着服务器在等待读
        raise HttpError('invalid http headers')
    request_method, path_info, protocol = s.strip().split()
    if '?' in path_info:
        path_info, query_string = path_info.split('?')
    else:
        path_info, query_string = path_info, ''
    base_uri, script_name = path_info.split('/', 1)
    if '' == script_name:
        script_name = app.config.default_page
    environ['REMOTE_ADDR'] = address
    environ['REMOTE_HOST'] = address[0]
    environ['REMOTE_PORT'] = address[1]
    environ['REQUEST_METHOD'] = request_method
    environ['QUERY_STRING'] = query_string
    environ['SERVER_PROTOCOL'] = protocol
    environ['SCRIPT_NAME'] = script_name
    environ['PATH_INFO'] = path_info
    s = rw.readline(DEFAULT_BUFFER_SIZE)
    while True:
        if s in EOFS:
            break
        k, v = s.split(':', 1)
        k, v = k.strip(), v.strip()
        k = k.replace('-', '_').upper()
        if k in environ:
            continue
        if k.startswith('_'):
            environ[k] = v
        else:
            environ['HTTP_%s' % k] = v
        s = rw.readline(DEFAULT_BUFFER_SIZE)
    size = environ.pop('HTTP_CONTENT_LENGTH', None)
    if not size:
        return environ
    size = int(size)
    content_type = environ.get('HTTP_CONTENT_TYPE', '')
    if content_type.startswith('multipart/form-data'):
        boundary = content_type.split('=')[1]
        begin_boundary = ('--%s' % boundary)
        end_boundary = ('--%s--' % boundary)
        files = {}
        s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
        while True:
            if s.strip() != begin_boundary:
                assert s.strip() == end_boundary
                break
            headers = {}
            s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
            while s:
                k, v = s.split(':', 1)
                headers[k.strip().upper()] = v.strip()
                s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
            disposition = headers['CONTENT-DISPOSITION']
            h, m, t = disposition.split(';')
            name = m.split('=')[1].strip()
            if size <= 5242880: # <= 5M file save in memory
                fp = StringIO()
            else:
                fp = TemporaryFile(mode='w+b')
            s = rw.readline(DEFAULT_BUFFER_SIZE)
            while s.strip() != begin_boundary \
                    and s.strip() != end_boundary:
                fp.write(s)
                s = rw.readline(DEFAULT_BUFFER_SIZE)
            fp.seek(0)
            files[name[1:-1]] = fp
        environ[FILES_HEADER_NAME] = files
    else:
        environ['POST_CONTENT'] = rw.read(int(size))
        environ['CONTENT_LENGTH'] = len(environ['POST_CONTENT'])
    return environ

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
        with GzipFile(fileobj=stream, mode="w") as f:
            f.write(text)
        self.gzip_text = gzip_text = stream.getvalue()
        self.gzip_etag = sha1(gzip_text).hexdigest()
        self.last_modified = gmt_date(stat(path).st_mtime)
        mimetype, coding = guess_type(name)
        headers = [('Content-Type', 'text/html;charset=utf-8')]
        if mimetype is not None:
            headers = [('Content-Type', '%s;charset=utf-8' % mimetype)]
        else:
            headers = [('Content-Type', 'application/octet-stream;charset=utf-8')]
        headers.append(('Last-Modified', self.last_modified))
        headers.append(('Connection', 'close'))
        self.headers = headers

    def handler(self, httpfile):
        environ = httpfile.environ
        if_modified_since = environ.get('HTTP_IF_MODIFIED_SINCE')
        if if_modified_since == self.last_modified:
            result = httpfile._response(304)
            return httpfile._finish(result)
        if_none_match = environ.get('HTTP_IF_NONE_MATCH')
        accept_encodings = environ.get(
            'HTTP_ACCEPT_ENCODING', '').split(',')
        accept_encodings = [s.strip().lower() for s in accept_encodings]
        headers = list(self.headers)
        if 'gzip' in accept_encodings:
            if if_none_match == self.gzip_etag:
                result = httpfile._response(304)
                return httpfile._finish(result)
            headers.append(('Etag', self.gzip_etag))
            headers.append(('Content-Encoding', 'gzip'))
            text = self.gzip_text
        elif 'deflate' in accept_encodings:
            if if_none_match == self.zlib_etag:
                result = httpfile._response(304)
                return httpfile._finish(result)
            headers.append(('Etag', self.zlib_etag))
            headers.append(('Content-Encoding', 'deflate'))
            text = self.zlib_text
        else:
            if if_none_match == self.etag:
                result = httpfile._response(304)
                return httpfile._finish(result)
            headers.append(('Etag', self.etag))
            text = self.text
        headers.append(('Content-Length', '%d' % len(text)))
        result = httpfile._response(200, headers=headers, content=text)
        return httpfile._finish(result)

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

class HttpFile(object):

    def __init__(self, app, rw, environ, address):
        self._rw = rw
        self._app = app
        self._environ = environ
        self._address = address
        self._buffers = StringIO()
        self._headers_responsed = False
        self._form = make_form(environ)
        self._session_id, self._session = self._get_session(environ)
        self._files = environ.pop(FILES_HEADER_NAME, None)

    def _get_session(self, environ):
        app = self._app
        sessions = app.sessions
        cookie = environ.get('HTTP_COOKIE')
        cookie = SimpleCookie(cookie)
        morsel = cookie.get(default_litefs_sid)
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
            session_id = sha1(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

    @property
    def config(self):
        return self._app.config

    @property
    def address(self):
        return self._address

    @property
    def files(self):
        return self._files

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
    def path_info(self):
        return self.environ['PATH_INFO']

    @property
    def query_string(self):
        return self.environ['QUERY_STRING']

    @property
    def request_uri(self):
        environ = self.environ
        path_info    = environ['PATH_INFO']
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
        buffers.write('HTTP/1.1 %d %s\r\n' % (status_code, status_text))
        for name, text in response_headers.items():
            buffers.write('%s: %s\r\n' % (name, text))
        if headers is not None:
            for header in headers:
                if isinstance(header, basestring):
                    buffers.write(header)
                else:
                    buffers.write('%s: %s\r\n' % header)
        if self.session_id is None:
            cookie = SimpleCookie()
            cookie[default_litefs_sid] = self.session.id
            cookie[default_litefs_sid]['path'] = '/'
            buffers.write('%s\r\n' % cookie.output())
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

    def _finish(self, content):
        rw = self._rw
        if not self._headers_responsed:
            self.start_response(200)
        rw.write(self._buffers.getvalue())
        if isinstance(content, basestring):
            rw.write(content)
        elif isinstance(content, dict):
            rw.write(repr(content))
        elif isinstance(content, Iterable):
            for s in content:
                if isinstance(s, basestring):
                    rw.write(s)
                else:
                    rw.write(repr(s))
        else:
            rw.write(repr(content))
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

    def _handler(self):
        app = self._app
        environ = self.environ
        path_info = environ['PATH_INFO']
        path = startswith_dot_sub('/', path_info)
        path = double_slash_sub('/', path)
        if path != path_info:
            result = self.redirect(path)
            try:
                return self._finish(result)
            except:
                content = exceptions.html_error_template().render()
                result = self._response(500, content=content)
                return self._finish(result)
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
                    content = exceptions.html_error_template().render()
                    result = self._response(500, content=content)
                    return self._finish(result)
                result = self._response(500)
                return self._finish(result)
            else:
                try:
                    return self._finish(result)
                except:
                    result = exceptions.html_error_template().render()
                    return self._finish(result)
        litefile = app.files.get(path)
        if litefile is not None:
            return litefile.handler(self)
        realpath = path_abspath(
            path_join(app.config.webroot, path.lstrip('/'))
        )
        if path_isdir(realpath):
            result = self.redirect(path + '/')
            return self._finish(result)
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
                    content = exceptions.html_error_template().render()
                    result = self._response(500, content=content)
                    return self._finish(result)
                result = self._response(500)
                return self._finish(result)
            else:
                try:
                    return self._finish(result)
                except:
                    result = exceptions.html_error_template().render()
                    return self._finish(result)
        try:
            litefile = self._load_static_file(base, name)
        except IOError:
            log_error(app.logger)
            result = self._response(404)
            return self._finish(result)
        if litefile is not None:
            app.files.put(path, litefile)
            try:
                return litefile.handler(self)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = exceptions.html_error_template().render()
                    result = self._response(500, content=content)
                    return self._finish(result)
                result = self._response(500)
                return self._finish(result)
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
                    content = exceptions.html_error_template().render()
                    result = self._response(500, content=content)
                    return self._finish(result)
                result = self._response(500)
                return self._finish(result)
        result = self._response(404)
        return self._finish(result)

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
                        content = exceptions.html_error_template().render()
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
        if ext in ('.pl', '.py', '.pyc', '.pyo', '.php') and \
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
                content = exceptions.html_error_template().render()
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
        level = logging.DEBUG if config.debug else logging.ERROR
        self.logger = make_logger(__name__, level=level)
        self.server_info = server_info = make_server(
            config.address, request_size=config.request_size
        )
        self.address = address = server_info['address']
        self.fileno = fileno = server_info['fileno']
        self.socket = server_info['socket']
        self.sessions = MemoryCache(max_size=1000000)
        self.caches = TreeCache()
        self.files  = TreeCache()
        self.epoll = select_epoll()
        self.epoll.register(fileno, EPOLLIN | EPOLLET)
        self.grs = {}
        sys.stdout.write((
            ' * Server is running at http://%s/\n'
            ' * Press ctrl-c to quit.\n\n'
        ) % address)

    def _handler_accept(self):
        while True:
            try:
                sock, address = self.socket.accept()
            except socket.error as e:
                errno = e.args[0]
                if EAGAIN == errno or EWOULDBLOCK == errno:
                    return
                raise
            sock.setblocking(0)
            fileno = sock.fileno()
            raw = RawIO(self, sock)
            self.grs[fileno] = gr = greenlet(
                partial(self._handler_io, raw, address)
            )
            gr.switch()

    def _handler_io(self, raw, address):
        try:
            config = self.config
            fileno = raw.fileno()
            rw = BufferedRWPair(raw, raw, DEFAULT_BUFFER_SIZE)
            environ = make_environ(self, rw, address)
            httpfile = HttpFile(self, rw, environ, address)
            if config.debug:
                log_debug(self.logger,
                    '%s - "%s %s %s"' % (
                        environ['REMOTE_HOST'],
                        environ['SERVER_PROTOCOL'],
                        environ['REQUEST_METHOD'],
                        environ['PATH_INFO']
                    )
                )
            httpfile._handler()
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
                self.grs.pop(fileno, None)
                try:
                    raw.close()
                except:
                    pass

    def _poll(self, timeout=.2):
        while True:
            events = self.epoll.poll(timeout)
            for fileno, event in events:
                if fileno == self.fileno:
                    try:
                        self._handler_accept()
                    except KeyboardInterrupt:
                        break
                    except socket.error as e:
                        if e.errno == EMFILE:
                            raise
                        log_error(self.logger)
                    except:
                        log_error(self.logger)
                elif event & EPOLLIN:
                    try:
                        self.grs[fileno].switch()
                    except KeyboardInterrupt:
                        break
                    except:
                        log_error(self.logger)
                elif event & EPOLLOUT:
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
            self._poll(timeout=timeout)
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

def test_server():
    import argparse
    parser = argparse.ArgumentParser(description='Litefs with epoll')
    parser.add_argument('--host', action="store", dest="host",
        required=False, default=default_host)
    parser.add_argument('--port', action="store", dest="port", type=int,
        required=False, default=default_port)
    parser.add_argument('--webroot', action="store", dest="webroot",
        required=False, default=default_webroot)
    parser.add_argument('--debug', action="store", dest="debug",
        required=False, default=False)
    parser.add_argument('--not-found', action="store", dest="not_found",
        required=False, default=default_404)
    parser.add_argument('--default-page', action="store",
        dest="default_page", required=False, default=default_page)
    parser.add_argument('--cgi-dir', action="store", dest="cgi_dir",
        required=False, default=default_cgi_dir)
    args = parser.parse_args()
    litefs = Litefs(
        address='%s:%d' % (args.host, args.port),
        webroot=args.webroot,
        debug=args.debug,
        default_page=args.default_page,
        not_found=args.not_found,
        cgi_dir=args.cgi_dir
    )
    litefs.run(timeout=2.)

if '__main__' == __name__:
    test_server()
