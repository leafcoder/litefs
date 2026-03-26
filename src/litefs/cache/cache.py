#!/usr/bin/env python
# coding: utf-8

import sqlite3
import time
from collections import deque
from hashlib import sha1
from gzip import GzipFile
from io import BytesIO
from mimetypes import guess_type
from os import stat
from posixpath import splitext as path_splitext
from watchdog.events import FileSystemEventHandler
from weakref import proxy
from zlib import compress

from ..utils import gmt_date, log_info

suffixes = (".py", ".pyc", ".pyo", ".so")


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
        stream = BytesIO()
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
        self.clean_time = time.time()
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
        if self.clean_time + self.clean_period < time.time():
            self.auto_clean()
        timestamp = int(time.time())
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
        if self.clean_time + self.clean_period < time.time():
            self.auto_clean()
        ret = data.get(key)
        if ret is None:
            return None
        val, timestamp = ret
        if int(time.time() - timestamp) > self.expiration_time:
            del data[key]
            return None
        return val

    def delete(self, key):
        conn = self.conn
        data = self.data
        if self.clean_time + self.clean_period < time.time():
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
        last_expiration_time = int(time.time() - self.expiration_time)
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
