#!/usr/bin/env python
# coding: utf-8

import os
import sqlite3
import time
from collections import OrderedDict, deque
from gzip import GzipFile
from hashlib import sha1
from io import BytesIO
from mimetypes import guess_type
from os import stat
from posixpath import splitext as path_splitext
from weakref import proxy
from zlib import compress

from watchdog.events import FileSystemEventHandler

from ..utils import gmt_date, log_info
from .base import CacheBackendBase

suffixes = (".py", ".pyc", ".pyo", ".so")


class FileEventHandler(FileSystemEventHandler):

    def __init__(self, app):
        FileSystemEventHandler.__init__(self)
        self._app = proxy(app)
        self._monitored_files = set()  # 记录已监控的文件
        self._last_reload_time = 0  # 上次重载时间
        self._reload_cooldown = 1.0  # 重载冷却时间（秒）

    def _should_reload(self, path):
        """
        判断文件变化是否需要重新加载应用
        
        Args:
            path: 文件路径
            
        Returns:
            True 表示需要重新加载，False 表示不需要
        """
        # 排除不需要触发重载的文件
        # 日志文件
        if path.endswith('.log'):
            return False
        # Python 编译文件
        if path.endswith(('.pyc', '.pyo', '.so')):
            return False
        # 临时文件和备份文件（包括 ~, .bak, .tmp, .swp 等）
        if path.endswith(('~', '.bak', '.tmp', '.swp', '.orig')):
            return False
        # 检查文件名是否包含波浪号（某些编辑器创建的备份文件）
        if '~' in os.path.basename(path):
            return False
        # __pycache__ 目录
        if '/__pycache__/' in path or path.startswith('__pycache__/'):
            return False
        # .git 目录
        if '/.git/' in path or path.startswith('.git/'):
            return False
        # .svn 目录
        if '/.svn/' in path or path.startswith('.svn/'):
            return False
        # .hg 目录
        if '/.hg/' in path or path.startswith('.hg/'):
            return False
        # node_modules 目录
        if '/node_modules/' in path:
            return False
        
        # Python 源文件变化需要重新加载
        if path.endswith('.py'):
            return True
        # 配置文件变化需要重新加载
        if path.endswith(('.yaml', '.yml', '.json', '.ini', '.conf')):
            return True
        return False

    def _can_reload_now(self):
        """
        检查现在是否可以触发重载（防止频繁重载）
        
        Returns:
            True 表示可以触发重载，False 表示需要等待
        """
        import time
        current_time = time.time()
        if current_time - self._last_reload_time >= self._reload_cooldown:
            self._last_reload_time = current_time
            return True
        return False

    def add_monitored_file(self, path):
        """
        添加需要监控的文件
        
        Args:
            path: 文件路径
        """
        self._monitored_files.add(path)

    def _reload_app(self, event_type, path):
        """
        重新加载应用
        
        Args:
            event_type: 事件类型
            path: 文件路径
        """
        # 检查是否可以触发重载（防止频繁重载）
        if not self._can_reload_now():
            return
        
        log_info(self._app.logger, "File %s: %s, reloading application..." % (event_type, path))
        
        # 标记需要重新加载
        self._app._need_reload = True
        
        # 清除所有缓存
        self._app.caches.data.clear()
        
        # 关闭服务器，触发重新加载
        if hasattr(self._app, 'server') and self._app.server:
            try:
                self._app.server.server_close()
            except Exception:
                pass

    def on_moved(self, event):
        src_path = event.src_path
        dest_path = event.dest_path
        
        # 对于移动事件，需要特殊处理
        # 如果是 .py 文件移动到备份文件（如 quickstart.py -> quickstart.py~），不触发重载
        # 这是编辑器保存文件时的常见行为
        src_is_backup = src_path.endswith('~') or '~' in os.path.basename(src_path)
        dest_is_backup = dest_path.endswith('~') or '~' in os.path.basename(dest_path)
        
        # 如果源文件或目标文件是备份文件，不触发重载
        if src_is_backup or dest_is_backup:
            return
        
        # 对于不需要触发重载的文件，不记录日志，避免循环触发
        if not self._should_reload(src_path) and not self._should_reload(dest_path):
            return
        
        log_info(self._app.logger, "%s has been moved to %s" % (src_path, dest_path))
        
        # 判断是否需要重新加载应用
        if self._should_reload(src_path) or self._should_reload(dest_path):
            self._reload_app('moved', dest_path)
        else:
            # 只清空缓存
            self._app.caches.data.clear()

    def on_created(self, event):
        src_path = event.src_path
        
        # 对于不需要触发重载的文件，不记录日志，避免循环触发
        if not self._should_reload(src_path):
            return
        
        log_info(self._app.logger, "%s has been created" % src_path)
        
        # 判断是否需要重新加载应用
        if self._should_reload(src_path):
            self._reload_app('created', src_path)
        else:
            # 只清空缓存
            self._app.caches.data.clear()

    def on_modified(self, event):
        src_path = event.src_path
        
        # 对于不需要触发重载的文件，不记录日志，避免循环触发
        if not self._should_reload(src_path):
            return
        
        log_info(self._app.logger, "%s has been modified" % src_path)
        
        # 判断是否需要重新加载应用
        if self._should_reload(src_path):
            self._reload_app('modified', src_path)
        else:
            # 只清空缓存
            self._app.caches.data.clear()

    def on_deleted(self, event):
        src_path = event.src_path
        
        # 对于不需要触发重载的文件，不记录日志，避免循环触发
        if not self._should_reload(src_path):
            return
        
        log_info(self._app.logger, "%s has been deleted" % src_path)
        
        # 判断是否需要重新加载应用
        if self._should_reload(src_path):
            self._reload_app('deleted', src_path)
        else:
            # 只清空缓存
            self._app.caches.data.clear()


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
        accept_encodings = environ.get("HTTP_ACCEPT_ENCODING", "").split(",")
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
        return request._response(self.status_code, headers=headers, content=text)


class TreeCache(CacheBackendBase):

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

    def put(self, key, val, expiration=None):
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self.clean_time >= self.clean_period:
            self.auto_clean()
        
        # 使用传入的 expiration 或默认的 expiration_time
        effective_expiration = expiration if expiration is not None else self.expiration_time
        
        timestamp = int(current_time)
        if key not in self.data:
            self.conn.execute(
                """
                INSERT INTO cache (key, timestamp) VALUES (?, ?);
            """,
                (key, timestamp),
            )
        else:
            self.conn.execute(
                """
                UPDATE cache SET timestamp=? WHERE key=?;
            """,
                (timestamp, key),
            )
        # 存储 [值, 时间戳, 过期时间] 三元组
        self.data[key] = [val, timestamp, effective_expiration]

    def get(self, key):
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self.clean_time >= self.clean_period:
            self.auto_clean()
        
        ret = self.data.get(key)
        if ret is None:
            return None
        val, timestamp, expiration = ret[0], ret[1], ret[2] if len(ret) > 2 else self.expiration_time
        if int(current_time - timestamp) > expiration:
            del self.data[key]
            return None
        return val

    def delete(self, key):
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self.clean_time >= self.clean_period:
            self.auto_clean()
        
        curr = self.conn.execute(
            """\
            SELECT key FROM cache WHERE key=? OR key LIKE ?;
        """,
            (key, key + "/%"),
        )
        keys = curr.fetchall()
        self.conn.executemany(
            """\
            DELETE FROM cache WHERE key=?;
        """,
            keys,
        )
        for item in keys:
            item_key = item[0]
            if item_key in self.data:
                del self.data[item_key]

    def auto_clean(self):
        """优化的清理机制
        
        避免每次清理都查询数据库，只在清理周期到达时执行清理
        """
        current_time = time.time()
        
        # 检查是否达到清理周期，避免频繁清理
        if current_time - self.clean_time < self.clean_period:
            return
        
        # 使用批量删除，避免先查询再删除（默认过期时间）
        self.conn.execute(
            "DELETE FROM cache WHERE timestamp < ?;",
            (int(current_time - self.expiration_time),)
        )
        
        # 清理内存缓存，考虑每条记录的独立过期时间
        expired_keys = [
            k for k, v in self.data.items()
            if current_time - v[1] > (v[2] if len(v) > 2 else self.expiration_time)
        ]
        for key in expired_keys:
            del self.data[key]
        
        # 更新清理时间
        self.clean_time = current_time

    def exists(self, key):
        """检查键是否存在且未过期"""
        return self.get(key) is not None

    def clear(self):
        """清空所有缓存"""
        self.data.clear()
        self.conn.execute("DELETE FROM cache")
        self.clean_time = time.time()

    def close(self):
        """关闭数据库连接"""
        try:
            if self.conn:
                self.conn.close()
        except Exception:
            pass


class MemoryCache(CacheBackendBase):

    def __init__(self, max_size=10000):
        self._max_size = int(max_size)
        self._cache = OrderedDict()

    def __str__(self):
        return str(self._cache)

    def __len__(self):
        return len(self._cache)

    def put(self, key, val, expiration=None):
        if key in self._cache:
            del self._cache[key]
        elif len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[key] = val

    def get(self, key):
        val = self._cache.get(key)
        if val is None:
            return None
        self._cache.move_to_end(key)
        return val

    def delete(self, key):
        if key not in self._cache:
            return
        del self._cache[key]

    def exists(self, key):
        """检查键是否存在"""
        return key in self._cache

    def clear(self):
        """清空所有缓存"""
        self._cache.clear()

    def close(self):
        """关闭（内存缓存无需操作）"""
        pass
