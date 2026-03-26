#!/usr/bin/env python
# coding: utf-8

import itertools
import json
import re
import sys
from collections import UserDict
from functools import partial
from http.cookies import SimpleCookie
from io import StringIO, BytesIO, RawIOBase, BufferedRWPair, DEFAULT_BUFFER_SIZE
from os import urandom
from posixpath import join as path_join, splitext as path_splitext, split as path_split, \
    abspath as path_abspath, isdir as path_isdir, exists as path_exists, \
    isfile as path_isfile, realpath as path_realpath
from subprocess import Popen, PIPE
from tempfile import NamedTemporaryFile, TemporaryFile
from time import time
from uuid import uuid4
from weakref import proxy
from mako.lookup import TemplateLookup
from hashlib import sha256
from errno import EWOULDBLOCK, EAGAIN
import importlib.util

try:
    from cgi import parse_header
except ImportError:
    from email.message import Message
    def parse_header(line):
        msg = Message()
        msg['content-type'] = line
        return msg.get_params()[0], dict(msg.get_params()[1:])

from urllib.parse import unquote_plus

from .cache import LiteFile
from .exceptions import HttpError
from .session import Session
from .utils import log_error, log_debug, render_error, gmt_date

import socket
from http.client import responses as http_status_codes
from io import BytesIO as StringIO

default_page = "index.html"
default_404 = "not_found"
default_sid = "litefs.sid"
default_content_type = "text/plain; charset=utf-8"

EOFS = ("", "\n", "\r\n")
POSTS_HEADER_NAME = "litefs.posts"
FILES_HEADER_NAME = "litefs.files"
should_retry_error = (EWOULDBLOCK, EAGAIN)
double_slash_sub = re.compile(r"\/{2,}").sub
startswith_dot_sub = re.compile(r"\/\.+").sub
suffixes = (".py", ".pyc", ".pyo", ".so", ".mako")
cgi_suffixes = (".pl", ".pyc", ".pyo", ".php")
form_dict_match = re.compile(r"(.+)\[([^\[\]]+)\]").match
server_info = "litefs/%s python/%s" % ("0.3.0", sys.version.split()[0])
cgi_runners = {
    ".pl": "/usr/bin/perl",
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

def is_unicode(s):
    return isinstance(s, str)

def is_bytes(s):
    return isinstance(s, bytes)

def imap(func, iterable):
    return map(func, iterable)

from hashlib import sha1


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


class WSGIRequestHandler(object):
    """
    WSGI 请求处理器，用于在 gunicorn、uWSGI 等 WSGI 服务器中运行
    
    符合 PEP 3333 规范，处理 WSGI environ 并返回标准响应
    """

    def __init__(self, app, environ):
        self._app = app
        self._environ = self._normalize_environ(environ)
        self._headers = []
        self._status_code = 200
        self._get = parse_form(self._environ.get("QUERY_STRING", ""))
        self._post = {}
        self._body = ""
        self._files = {}
        self._session_id = None
        self._session = None
        self._headers_responsed = False
        
        content_type = self._environ.get("CONTENT_TYPE", "")
        if content_type:
            content_type, params = parse_header(content_type)
            content_length_str = self._environ.get("CONTENT_LENGTH") or "0"
            content_length = int(content_length_str) if content_length_str.strip() else 0
            
            if content_length > 0:
                max_request_size = getattr(app.config, 'max_request_size', 10485760)
                if content_length > max_request_size:
                    raise HttpError(413, f"Request body too large. Maximum size is {max_request_size} bytes")
            
            if content_type == 'application/x-www-form-urlencoded':
                if content_length > 0:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        post_content = wsgi_input.read(content_length)
                        post_content = post_content.decode("utf-8")
                        self._post = parse_form(post_content)
            elif content_type == 'multipart/form-data':
                boundary = params.get("boundary")
                if boundary:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        content_length_str = self._environ.get("CONTENT_LENGTH") or "0"
                        content_length = int(content_length_str) if content_length_str.strip() else 0
                        if content_length > 0:
                            self._parse_multipart(wsgi_input, boundary, 
                                                 content_length)
            else:
                if content_length > 0:
                    wsgi_input = self._environ.get("wsgi.input")
                    if wsgi_input:
                        self._body = wsgi_input.read(content_length)
                        self._body = self._body.decode("utf-8")
        
        self._session_id, self._session = self._get_session()
        
        if app.config.debug:
            log_debug(app.logger, "%s - \"%s %s %s\"" % (
                self._environ.get("REMOTE_ADDR", "-"),
                self._environ.get("SERVER_PROTOCOL", "HTTP/1.1"),
                self._environ.get("REQUEST_METHOD", "GET"),
                self._environ.get("PATH_INFO", "/")
            ))

    def _normalize_environ(self, environ):
        normalized = dict(environ)
        
        if "PATH_INFO" not in normalized:
            normalized["PATH_INFO"] = "/"
        
        if "REQUEST_METHOD" not in normalized:
            normalized["REQUEST_METHOD"] = "GET"
        
        if "QUERY_STRING" not in normalized:
            normalized["QUERY_STRING"] = ""
        
        if "CONTENT_LENGTH" not in normalized:
            normalized["CONTENT_LENGTH"] = "0"
        else:
            content_length = normalized.get("CONTENT_LENGTH", "0")
            if content_length == "" or content_length is None:
                normalized["CONTENT_LENGTH"] = "0"
        
        if "CONTENT_TYPE" not in normalized:
            normalized["CONTENT_TYPE"] = ""
        
        if "HTTP_HOST" not in normalized:
            host = normalized.get("SERVER_NAME", "localhost")
            port = normalized.get("SERVER_PORT", "80")
            if port != "80":
                normalized["HTTP_HOST"] = "%s:%s" % (host, port)
            else:
                normalized["HTTP_HOST"] = host
        
        return normalized

    def _parse_multipart(self, wsgi_input, boundary, content_length):
        app = self._app
        max_upload_size = getattr(app.config, 'max_upload_size', 52428800)
        
        if content_length > max_upload_size:
            raise HttpError(413, f"Request body too large. Maximum size is {max_upload_size} bytes")
        
        boundary = boundary.encode("utf-8")
        begin_boundary = b"--" + boundary
        end_boundary = b"--" + boundary + b"--"
        
        posts = {}
        files = {}
        
        data = wsgi_input.read(content_length)
        
        parts = data.split(begin_boundary)
        
        for part in parts[1:]:
            if part.strip() == end_boundary:
                break
            
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            
            headers_part = part[:header_end]
            content = part[header_end + 4:]
            
            headers = {}
            for line in headers_part.split(b"\r\n"):
                if b":" in line:
                    k, v = line.split(b":", 1)
                    k = k.strip().upper()
                    v = v.strip()
                    k = k.decode("utf-8")
                    v = v.decode("utf-8")
                    headers[k] = v
            
            disposition = headers.get("CONTENT-DISPOSITION", "")
            disposition, params = parse_header(disposition)
            name = params.get("name", "")
            
            filename = params.get("filename")
            if filename:
                fp = TemporaryFile(mode="w+b")
                fp.write(content)
                fp.seek(0)
                files[name] = fp
            else:
                content = content.decode("utf-8")
                posts[name] = content.strip()
        
        self._post = posts
        self._files = files

    def _get_session(self):
        app = self._app
        sessions = app.sessions
        cookie_str = self._environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie(cookie_str)
        morsel = cookie.get(default_sid)
        
        if morsel is not None:
            session_id = morsel.value
            session = sessions.get(session_id)
            if session is not None:
                return session_id, session
        
        session_id = self._new_session_id()
        session = Session(session_id)
        sessions.put(session_id, session)
        return None, session

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while True:
            token = urandom(32)
            session_id = sha256(token).hexdigest()
            session = sessions.get(session_id)
            if session is None:
                break
        return session_id

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
        if not body:
            return {}
        content_type = self._environ.get("CONTENT_TYPE", "")
        content_type, _ = parse_header(content_type)
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
        return self._environ.get("REQUEST_METHOD", "GET")

    method = request_method

    @property
    def server_protocol(self):
        return self._environ.get("SERVER_PROTOCOL", "HTTP/1.1")

    @property
    def content_type(self):
        return self._environ.get("CONTENT_TYPE")

    @property
    def charset(self, default="UTF-8"):
        content_type = self.content_type
        if content_type:
            _, params = parse_header(content_type)
            return params.get("charset", default)
        return default

    @property
    def content_length(self):
        return int(self._environ.get("CONTENT_LENGTH", 0) or 0)

    @property
    def path_info(self):
        return self._environ.get("PATH_INFO", "/")

    @property
    def query_string(self):
        return self._environ.get("QUERY_STRING", "")

    @property
    def request_uri(self):
        path_info = self.path_info
        query_string = self.query_string
        if not query_string:
            return path_info
        return "?".join((path_info, query_string))

    @property
    def referer(self):
        return self._environ.get("HTTP_REFERER")

    @property
    def cookie(self):
        cookie_str = self._environ.get("HTTP_COOKIE", "")
        cookie = SimpleCookie()
        cookie.load(cookie_str)
        return cookie

    def set_cookie(self, name, value, **options):
        cookie_str = ""
        cookie_str += "%s=%s" % (name, value)
        
        for key, value in options.items():
            if not value:
                continue
            cookie_str += "; %s=%s" % (key, value)
        
        self._headers.append(('Set-Cookie', cookie_str))

    def start_response(self, status_code=200, headers=None):
        if self._headers_responsed:
            raise ValueError("Http headers already responsed.")
        self._status_code = int(status_code)
        if headers is not None:
            for header in headers:
                if not isinstance(header, (list, tuple)):
                    header = header.encode("utf-8")
                    k, v = header.split(":")
                    k, v = k.strip(), v.strip()
                else:
                    k, v = header
                self._headers.append((k, v))
        self._headers_responsed = True

    def _response(self, status_code, headers=None, content=None):
        status_code = int(status_code)
        status_text = http_status_codes.get(status_code, "Unknown")
        status = "%d %s" % (status_code, status_text)
        
        response_headers = []
        response_headers.append(('Server', server_info))
        response_headers.append(('Content-Type', 'text/html; charset=utf-8'))
        
        if headers:
            response_headers.extend(headers)
        
        if self.session_id is None:
            self.set_cookie(default_sid, self.session.id, path="/")
        
        response_headers.extend(self._headers)
        
        if content is None:
            content = DEFAULT_STATUS_MESSAGE % {
                "code": status_code,
                "message": status_text,
                "explain": status_text
            }
        
        return status, response_headers, content

    def handler(self):
        app = self._app
        environ = self._environ
        path_info = environ.get("PATH_INFO", "/")
        
        path = startswith_dot_sub("/", path_info)
        path = double_slash_sub("/", path)
        
        if path != path_info:
            return self._redirect(path)
        
        base, name = path_split(path)
        if not name:
            name = default_page
        
        path = path_join(base, name)
        
        module = app.caches.get(path)
        if module is not None:
            try:
                result = module.handler(self)
                if isinstance(result, tuple) and len(result) == 3:
                    return result
                return self._response(200, content=result)
            except:
                log_error(app.logger)
                if app.config.debug:
                    content = render_error()
                    return self._response(500, content=content)
                return self._response(500)
        
        litefile = app.files.get(path)
        if litefile is not None:
            return self._handle_litefile(litefile)
        
        from posixpath import abspath as path_abspath, isdir as path_isdir
        realpath = path_abspath(
            path_join(app.config.webroot, path.lstrip("/"))
        )
        
        if path_isdir(realpath):
            return self._redirect(path + "/")
        
        name_without_ext, ext = path_splitext(name)
        
        if ext in ('.py', '.mako'):
            return self._response(404)
        
        script_extensions = ['.py', '.mako']
        for script_ext in script_extensions:
            script_name = name + script_ext
            script_path = path_join(base, script_name)
            module = self._load_script(base, script_name)
            if module is not None and hasattr(module, "handler"):
                if script_ext == ".mako":
                    app.caches.put(path_join(base, name), module)
                else:
                    app.caches.put(script_path, module)
                try:
                    result = module.handler(self)
                    if isinstance(result, tuple) and len(result) == 3:
                        return result
                    return self._response(200, content=result)
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
            return self._handle_litefile(litefile)
        
        return self._response(404)

    def _handle_litefile(self, litefile):
        environ = self._environ
        if_modified_since = environ.get("HTTP_IF_MODIFIED_SINCE")
        if if_modified_since == litefile.last_modified:
            return self._response(304)
        
        if_none_match = environ.get("HTTP_IF_NONE_MATCH")
        accept_encodings = environ.get(
            "HTTP_ACCEPT_ENCODING", "").split(",")
        accept_encodings = [s.strip().lower() for s in accept_encodings]
        
        headers = list(litefile.headers)
        
        if "gzip" in accept_encodings:
            if if_none_match == litefile.gzip_etag:
                return self._response(304)
            headers.append(("Etag", litefile.gzip_etag))
            headers.append(("Content-Encoding", "gzip"))
            text = litefile.gzip_text
        elif "deflate" in accept_encodings:
            if if_none_match == litefile.zlib_etag:
                return self._response(304)
            headers.append(("Etag", litefile.zlib_etag))
            headers.append(("Content-Encoding", "deflate"))
            text = litefile.zlib_text
        else:
            if if_none_match == litefile.etag:
                return self._response(304)
            headers.append(("Etag", litefile.etag))
            text = litefile.text
        
        headers.append(("Content-Length", "%d" % len(text)))
        return self._response(litefile.status_code, headers=headers, content=text)

    def _redirect(self, url):
        url = '/' if url is None else url
        headers = [
            ("Content-Type", "text/html; charset=utf-8"),
            ("Location", url)
        ]
        status_code = 302
        status_text = http_status_codes.get(status_code, "Found")
        content = "%d %s" % (status_code, status_text)
        return self._response(status_code, headers=headers, content=content)

    def _load_script(self, base, name):
        app = self._app
        webroot = app.config.webroot
        script_path = path_join(webroot, base.lstrip("/"), name)
        
        from posixpath import exists as path_exists
        if not path_exists(script_path):
            return None
        
        ext = path_splitext(name)[1]
        
        if ext in cgi_suffixes:
            return self._load_cgi_script(script_path)
        
        if ext == ".mako":
            return self._load_template(base, name)
        
        if ext in suffixes:
            return self._load_python_script(script_path)
        
        return None

    def _load_python_script(self, script_path):
        app = self._app
        fp = None
        try:
            sys.dont_write_bytecode = True
            module_name = path_splitext(path_split(script_path)[1])[0]
            fp = open(script_path, "rb")
            module = new_module()
            setattr(module, 'handler', self)
            code = compile(fp.read(), script_path, 'exec')
            module_globals = {}
            exec(code, module_globals)
            for k, v in module_globals.items():
                setattr(module, k, v)
            return module
        except:
            log_error(app.logger)
            return None
        finally:
            sys.dont_write_bytecode = False
            if fp:
                fp.close()

    def _load_cgi_script(self, script_path):
        app = self._app
        webroot = app.config.webroot
        ext = path_splitext(script_path)[1]
        runner = cgi_runners.get(ext)
        
        if not runner:
            return None
        
        tmpf = NamedTemporaryFile("w+")
        try:
            p = Popen(
                [runner, script_path],
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
            
            tmpf.seek(0)
            if not stderr:
                stdout = tmpf.read()
            
            module = new_module()
            module.handler = lambda self: stdout
            return module
        finally:
            tmpf.close()

    def _load_template(self, base, name):
        app = self._app
        webroot = app.config.webroot
        script_uri = path_join(base.lstrip("/"), name)
        path = path_join("/%s" % base.rstrip("/"), name)
        from mako.lookup import TemplateLookup
        mylookup = TemplateLookup(directories=[webroot])
        def handler(mylookup, script_uri):
            def _handler(self):
                try:
                    template = mylookup.get_template(script_uri)
                    content = template.render(http=self)
                    headers = getattr(template.module, "headers", None)
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

    def _load_static_file(self, base, name):
        app = self._app
        webroot = app.config.webroot
        file_path = path_join(webroot, base.lstrip("/"), name)
        
        from posixpath import isfile as path_isfile
        if not path_isfile(file_path):
            raise IOError("File not found: %s" % file_path)
        
        with open(file_path, "rb") as fp:
            text = fp.read()
        
        return LiteFile(file_path, base, name, text)


def new_module(**kwargs):
    name = "".join(("litefs", uuid4().hex))
    module = type(name, (), {})
    for k, v in kwargs.items():
        setattr(module, k, v)
    return module


def parse_multipart(rw, content_type):
    boundary = content_type.split("=")[1].strip()
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
            s = s.decode("utf-8")
            k, v = s.split(":", 1)
            headers[k.strip().upper()] = v.strip()
            s = rw.readline(DEFAULT_BUFFER_SIZE).strip()
        disposition = headers["CONTENT-DISPOSITION"]
        disposition, params = parse_header(disposition)
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


class RequestHandler(object):

    default_headers = {
        "Content-Type": default_content_type
    }

    def __init__(self, app, rw, environ, request):
        self._request = request
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
        content_type, params = parse_header(content_type)
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
        return None, session

    def _new_session_id(self):
        app = self._app
        sessions = app.sessions
        while True:
            token = urandom(32)
            session_id = sha256(token).hexdigest()
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
        content_type, _ = parse_header(content_type)
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
        _, params = parse_header(self.content_type)
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
        line = line.encode("utf-8")
        rw.write(line)
        headers = self._response_headers
        if not headers:
            headers = self.default_headers
        for header, value in headers.items():
            line = "%s: %s\r\n" % (header, value)
            line = line.encode("utf-8")
            rw.write(line)
        if self._cookies:
            for c in self._cookies.values():
                line = "%s: %s\r\n" % ('Set-Cookie', c.OutputString())
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
        
        name_without_ext, ext = path_splitext(name)
        if ext in ('.py', '.mako'):
            return self._response(404)
        
        path = path_join(base, name)
        module = app.caches.get(path)
        if module is not None:
            try:
                result = module.handler(self)
                if isinstance(result, tuple) and len(result) == 3:
                    return result
                return self._response(200, content=result)
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
                result = module.handler(self)
                if isinstance(result, tuple) and len(result) == 3:
                    return result
                return self._response(200, content=result)
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
        script_path = path_join(realbase, name)
        if not path_exists(script_path):
            return None
        module_name = "litefs_%s" % uuid4().hex
        sys.dont_write_bytecode = True
        try:
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            if spec is None or spec.loader is None:
                return None
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)
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
