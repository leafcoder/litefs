#!/usr/bin/env python
# coding: utf-8

"""
服务器生命周期 Mixin

提供服务启动、信号处理、优雅关闭、WebSocket 联动与
基于文件修改时间的热重载能力。
"""

import logging
import os
import signal
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any, Optional, Union

from ..server import HTTPServer, ProcessHTTPServer, mainloop
from ..utils import log_error, log_info

if TYPE_CHECKING:
    from ..config import Config


class ServerMixin:
    """服务器启动、关闭与热重载生命周期管理

    依赖宿主 ``Litefs`` 装配时提供的属性与其他 Mixin 方法，
    以下声明仅供类型检查使用，运行时无开销。
    """

    #: 由 Litefs.__init__ 装配的宿主属性
    server: Optional[Union[HTTPServer, ProcessHTTPServer]]
    logger: logging.Logger
    host: str
    port: int
    config: "Config"

    if TYPE_CHECKING:
        # 跨 Mixin 方法：由 ExtensionMixin / ProtocolMixin / RoutingMixin 提供
        def load_plugins(self) -> Any: ...
        def get_websocket(self) -> Any: ...
        def handler(self, request, rw, environ, server) -> Any: ...

    def run(self, poll_interval=0.2, processes=1, reload=False):
        main_file = getattr(sys.modules['__main__'], '__file__', None)
        if main_file:
            main_file = os.path.abspath(main_file)

        is_child_process = os.environ.get('LITEFS_CHILD_PROCESS', '0') == '1'

        if not reload or is_child_process:
            self._run_server(poll_interval, processes)
        else:
            self._run_with_reload(main_file)

    def _run_server(self, poll_interval, processes):
        """启动服务器（无热重载）"""

        def signal_handler(signum, frame):
            if hasattr(self, 'server') and self.server:
                try:
                    if hasattr(self.server, 'shutdown'):
                        self.server.shutdown()
                except Exception as e:
                    log_error(
                        self.logger,
                        "Error shutting down server in signal handler: %s"
                        % str(e),
                    )
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self.load_plugins()

        ws_instance = self.get_websocket()
        if ws_instance:
            ws_instance.start()
            log_info(
                self.logger,
                "WebSocket server started on port %d" % (self.port + 1),
            )

        log_info(
            self.logger,
            "Starting server on %s:%d (processes=%d)"
            % (self.host, self.port, processes),
        )

        try:
            if processes > 1:
                self.server = ProcessHTTPServer(
                    (self.host, self.port), self.handler, processes=processes
                )
                self.server.max_request_size = self.config.max_request_size
                self.server.server_forever(poll_interval=poll_interval)
            else:
                self.server = HTTPServer((self.host, self.port), self.handler)
                self.server.max_request_size = self.config.max_request_size
                self.server.start()
                mainloop(poll_interval=poll_interval)
        except KeyboardInterrupt:
            log_info(self.logger, "Server stopped by user")
        except SystemExit:
            log_info(self.logger, "Server stopped by signal")
        except Exception as e:
            log_error(self.logger, "Server error: %s" % str(e))
        finally:
            self._cleanup_server()

    def _cleanup_server(self):
        """清理服务器资源"""
        ws_instance = self.get_websocket()
        if ws_instance:
            try:
                ws_instance.stop()
            except Exception as e:
                log_error(self.logger, "Error stopping WebSocket: %s" % str(e))
        if hasattr(self, 'server') and self.server:
            try:
                if hasattr(self.server, 'shutdown'):
                    self.server.shutdown()
                self.server.server_close()
            except Exception as e:
                log_error(self.logger, "Error closing server: %s" % str(e))
        try:
            from ..database import DatabaseManager
            DatabaseManager.close_all()
        except Exception as e:
            log_error(
                self.logger,
                "Error closing database connections: %s" % str(e),
            )

    def _scan_file_modtimes(self, watch_dirs):
        """扫描所有 Python 文件的修改时间"""
        mod_times = {}
        for watch_dir in watch_dirs:
            if not os.path.exists(watch_dir):
                continue
            for root, dirs, files in os.walk(watch_dir):
                dirs[:] = [
                    d for d in dirs
                    if not d.startswith('.') and d != '__pycache__'
                ]
                for file in files:
                    if file.endswith('.py'):
                        file_path = os.path.join(root, file)
                        try:
                            mod_times[file_path] = os.path.getmtime(file_path)
                        except OSError:
                            pass
        return mod_times

    def _check_file_changes(self, watch_dirs, file_mod_times):
        """检查文件是否有变化"""
        current_mod_times = self._scan_file_modtimes(watch_dirs)

        for file_path, mtime in current_mod_times.items():
            if file_path not in file_mod_times:
                return True
            if mtime != file_mod_times[file_path]:
                return True

        for file_path in file_mod_times:
            if file_path not in current_mod_times:
                return True

        return False

    def _run_with_reload(self, main_file: Optional[str]):
        """启动带热重载的服务器"""
        child_proc: Optional[subprocess.Popen] = None

        def parent_signal_handler(signum, frame):
            if child_proc and child_proc.poll() is None:
                try:
                    child_proc.terminate()
                    child_proc.wait(timeout=5)
                except Exception as e:
                    log_error(
                        self.logger,
                        "Error terminating child process: %s" % str(e),
                    )
                    try:
                        child_proc.kill()
                        child_proc.wait()
                    except Exception as e2:
                        log_error(
                            self.logger,
                            "Error killing child process: %s" % str(e2),
                        )
            sys.exit(0)

        signal.signal(signal.SIGINT, parent_signal_handler)
        signal.signal(signal.SIGTERM, parent_signal_handler)

        log_info(
            self.logger,
            "Starting server with hot reload on %s:%d" % (self.host, self.port),
        )

        if main_file:
            project_dir = os.path.dirname(main_file)
            watch_dirs = [project_dir]

            src_dir = os.path.join(os.path.dirname(project_dir), 'src')
            if os.path.exists(src_dir):
                watch_dirs.append(src_dir)
        else:
            watch_dirs = []

        file_mod_times = self._scan_file_modtimes(watch_dirs)

        while True:
            try:
                env = os.environ.copy()
                env['LITEFS_CHILD_PROCESS'] = '1'

                child_proc = subprocess.Popen(
                    [sys.executable] + sys.argv,
                    env=env,
                    close_fds=True
                )

                while child_proc.poll() is None:
                    time.sleep(1)

                    if self._check_file_changes(watch_dirs, file_mod_times):
                        log_info(self.logger, "File changed, restarting server...")
                        file_mod_times = self._scan_file_modtimes(watch_dirs)

                        try:
                            child_proc.terminate()
                            child_proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            child_proc.kill()
                            child_proc.wait()
                        except Exception as e:
                            log_error(
                                self.logger,
                                "Error terminating child process on file "
                                "change: %s" % str(e),
                            )
                        break

                exit_code = child_proc.returncode

                if exit_code == 0 or exit_code is None:
                    continue

                if exit_code not in (0, -2, -15):
                    log_error(
                        self.logger,
                        "Server exited with code %d" % exit_code,
                    )

                break

            except Exception as e:
                log_error(self.logger, "Error starting server: %s" % str(e))
                time.sleep(1)
            finally:
                if child_proc and child_proc.poll() is None:
                    try:
                        child_proc.terminate()
                        child_proc.wait(timeout=5)
                    except Exception as e:
                        log_error(
                            self.logger,
                            "Error terminating child process: %s" % str(e),
                        )
                        try:
                            child_proc.kill()
                            child_proc.wait()
                        except Exception as e2:
                            log_error(
                                self.logger,
                                "Error killing child process: %s" % str(e2),
                            )
