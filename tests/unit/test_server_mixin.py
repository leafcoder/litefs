#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
ServerMixin（服务器生命周期）单元测试

以最小宿主类承载 Mixin，全部外部依赖（HTTPServer / ProcessHTTPServer /
mainloop / subprocess / DatabaseManager）均打桩，不真正 fork 或监听端口。
覆盖：启动路径、信号处理、清理逻辑、热重载扫描与重启循环。
"""

import logging
import signal
import subprocess
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

from litefs.app.server_mixin import ServerMixin


class FakeApp(ServerMixin):
    """承载 ServerMixin 的最小宿主类"""

    def __init__(self):
        self.server = None
        self.logger = logging.getLogger('test.server_mixin')
        self.host = '127.0.0.1'
        self.port = 0
        self.config = Mock(max_request_size=1024)
        self.load_plugins = Mock()
        self.get_websocket = Mock(return_value=None)
        self.handler = Mock()


@pytest.fixture
def app():
    return FakeApp()


@pytest.fixture
def restore_signals():
    """保存并恢复进程信号处理器，避免污染 pytest 主线程"""
    saved_int = signal.getsignal(signal.SIGINT)
    saved_term = signal.getsignal(signal.SIGTERM)
    yield
    signal.signal(signal.SIGINT, saved_int)
    signal.signal(signal.SIGTERM, saved_term)


@pytest.fixture
def no_sleep():
    """热重载循环中的 sleep 打桩为空操作，避免测试拖慢"""
    with patch('litefs.app.server_mixin.time.sleep'):
        yield


def make_child(returncode, poll_seq):
    """构造模拟子进程：poll 按序返回，returncode 固定"""
    child = MagicMock()
    child.poll.side_effect = list(poll_seq)
    child.returncode = returncode
    return child


class TestRunDispatch:
    """run() 分发逻辑测试"""

    def test_run_without_reload_calls_run_server(self, app):
        """非热重载模式直接进入 _run_server"""
        with patch.object(app, '_run_server') as run_server:
            app.run(poll_interval=0.1, processes=1, reload=False)
        run_server.assert_called_once_with(0.1, 1)

    def test_run_with_reload_in_child_process_calls_run_server(self, app, monkeypatch):
        """子进程环境变量命中时即使 reload=True 也走 _run_server"""
        monkeypatch.setenv('LITEFS_CHILD_PROCESS', '1')
        with patch.object(app, '_run_server') as run_server:
            app.run(reload=True)
        run_server.assert_called_once()

    def test_run_with_reload_calls_run_with_reload(self, app, monkeypatch):
        """主进程 reload=True 走 _run_with_reload"""
        monkeypatch.delenv('LITEFS_CHILD_PROCESS', raising=False)
        main_mod = sys.modules['__main__']
        monkeypatch.setattr(main_mod, '__file__', '/tmp/main.py', raising=False)
        with patch.object(app, '_run_with_reload') as run_reload:
            app.run(reload=True)
        run_reload.assert_called_once()
        args = run_reload.call_args[0][0]
        assert args is None or args.endswith('main.py')


class TestRunServer:
    """_run_server 启动路径测试"""

    def test_single_process_startup(self, app, restore_signals):
        """单进程模式：创建 HTTPServer、注册 epoll、进入主循环"""
        with patch('litefs.app.server_mixin.HTTPServer') as server_cls, \
                patch('litefs.app.server_mixin.mainloop',
                      side_effect=KeyboardInterrupt):
            app._run_server(poll_interval=0.1, processes=1)

        server_cls.assert_called_once_with(
            ('127.0.0.1', 0), app.handler,
            request_queue_size=app.config.request_queue_size,
        )
        server = app.server
        assert server.max_request_size == 1024
        server.start.assert_called_once()
        # KeyboardInterrupt 触发 finally 清理
        app.load_plugins.assert_called_once()
        assert app.get_websocket.call_count >= 1

    def test_multi_process_startup(self, app, restore_signals):
        """多进程模式：创建 ProcessHTTPServer 并调用 server_forever"""
        with patch('litefs.app.server_mixin.ProcessHTTPServer') as server_cls:
            app._run_server(poll_interval=0.2, processes=4)

        server_cls.assert_called_once_with(
            ('127.0.0.1', 0), app.handler, processes=4,
            request_queue_size=app.config.request_queue_size,
        )
        app.server.max_request_size = 1024
        app.server.server_forever.assert_called_once_with(poll_interval=0.2)

    def test_system_exit_logged_as_signal_stop(self, app, restore_signals):
        """SystemExit 视为信号停止，正常走清理"""
        with patch('litefs.app.server_mixin.HTTPServer'), \
                patch('litefs.app.server_mixin.mainloop',
                      side_effect=SystemExit):
            app._run_server(poll_interval=0.1, processes=1)
        assert app.server is not None

    def test_generic_exception_logged(self, app, restore_signals):
        """主循环异常被记录并正常清理"""
        with patch('litefs.app.server_mixin.HTTPServer'), \
                patch('litefs.app.server_mixin.mainloop',
                      side_effect=RuntimeError('boom')):
            app._run_server(poll_interval=0.1, processes=1)
        assert app.server is not None

    def test_websocket_started_when_present(self, app, restore_signals):
        """WebSocket 实例存在时启动并在清理时停止"""
        ws = Mock()
        app.get_websocket = Mock(return_value=ws)
        with patch('litefs.app.server_mixin.HTTPServer'), \
                patch('litefs.app.server_mixin.mainloop',
                      side_effect=KeyboardInterrupt):
            app._run_server(poll_interval=0.1, processes=1)
        ws.start.assert_called_once()
        ws.stop.assert_called_once()

    def test_signal_handler_shuts_down_and_exits(self, app, restore_signals):
        """SIGTERM 处理器调用 server.shutdown 并退出进程"""
        with patch('litefs.app.server_mixin.HTTPServer'), \
                patch('litefs.app.server_mixin.mainloop',
                      side_effect=KeyboardInterrupt):
            app._run_server(poll_interval=0.1, processes=1)

        handler = signal.getsignal(signal.SIGTERM)
        with pytest.raises(SystemExit):
            handler(signal.SIGTERM, None)
        # 信号处理器与 finally 清理各调用一次
        assert app.server.shutdown.call_count == 2


class TestCleanupServer:
    """_cleanup_server 清理逻辑测试"""

    def test_cleanup_without_server(self, app):
        """无服务器实例时仅尝试关闭数据库"""
        app._cleanup_server()
        app.get_websocket.assert_called_once()

    def test_cleanup_stops_websocket(self, app):
        """清理时停止 WebSocket 并关闭服务器"""
        ws = Mock()
        app.get_websocket = Mock(return_value=ws)
        app.server = Mock()
        app._cleanup_server()
        ws.stop.assert_called_once()
        app.server.shutdown.assert_called_once()
        app.server.server_close.assert_called_once()

    def test_cleanup_websocket_error_swallowed(self, app):
        """WebSocket 停止异常不阻断后续清理"""
        ws = Mock()
        ws.stop.side_effect = RuntimeError('stop failed')
        app.get_websocket = Mock(return_value=ws)
        app.server = Mock()
        app._cleanup_server()
        app.server.server_close.assert_called_once()

    def test_cleanup_server_error_swallowed(self, app):
        """服务器关闭异常被吞掉"""
        app.server = Mock()
        app.server.server_close.side_effect = RuntimeError('close failed')
        app._cleanup_server()

    def test_cleanup_without_shutdown_method(self, app):
        """服务器无 shutdown 方法时仅调用 server_close"""
        app.server = Mock(spec=['server_close'])
        app._cleanup_server()
        app.server.server_close.assert_called_once()

    def test_cleanup_closes_database_manager(self, app):
        """清理时关闭全部数据库连接"""
        app.server = Mock()
        with patch('litefs.database.DatabaseManager.close_all') as close_all:
            app._cleanup_server()
        close_all.assert_called_once()

    def test_cleanup_database_error_swallowed(self, app):
        """数据库关闭异常被吞掉"""
        with patch('litefs.database.DatabaseManager.close_all',
                   side_effect=RuntimeError('db failed')):
            app._cleanup_server()


class TestFileModtimeScan:
    """文件修改时间扫描测试"""

    def test_scan_collects_py_files(self, app, tmp_path):
        """扫描收集 .py 文件的修改时间"""
        (tmp_path / 'a.py').write_text('x = 1')
        sub = tmp_path / 'sub'
        sub.mkdir()
        (sub / 'b.py').write_text('y = 2')
        (tmp_path / 'readme.txt').write_text('not python')

        mod_times = app._scan_file_modtimes([str(tmp_path)])
        assert str(tmp_path / 'a.py') in mod_times
        assert str(sub / 'b.py') in mod_times
        assert not any(k.endswith('readme.txt') for k in mod_times)

    def test_scan_skips_hidden_and_pycache(self, app, tmp_path):
        """隐藏目录与 __pycache__ 不参与扫描"""
        hidden = tmp_path / '.hidden'
        hidden.mkdir()
        (hidden / 'h.py').write_text('x = 1')
        cache = tmp_path / '__pycache__'
        cache.mkdir()
        (cache / 'c.py').write_text('x = 1')
        (tmp_path / 'top.py').write_text('x = 1')

        mod_times = app._scan_file_modtimes([str(tmp_path)])
        assert list(mod_times) == [str(tmp_path / 'top.py')]

    def test_scan_missing_dir_skipped(self, app, tmp_path):
        """不存在的目录被跳过"""
        assert app._scan_file_modtimes([str(tmp_path / 'nope')]) == {}

    def test_scan_unreadable_file_skipped(self, app, tmp_path, monkeypatch):
        """getmtime 抛 OSError 的文件被跳过"""
        target = tmp_path / 'a.py'
        target.write_text('x = 1')
        (tmp_path / 'b.py').write_text('x = 2')

        real_getmtime = __import__('os').path.getmtime

        def fake_getmtime(path):
            if path.endswith('a.py'):
                raise OSError('permission denied')
            return real_getmtime(path)

        monkeypatch.setattr('os.path.getmtime', fake_getmtime)
        mod_times = app._scan_file_modtimes([str(tmp_path)])
        assert str(target) not in mod_times
        assert str(tmp_path / 'b.py') in mod_times


class TestCheckFileChanges:
    """文件变化检测测试"""

    def test_no_change(self, app, tmp_path):
        """无变化返回 False"""
        f = tmp_path / 'a.py'
        f.write_text('x = 1')
        mod_times = app._scan_file_modtimes([str(tmp_path)])
        assert app._check_file_changes([str(tmp_path)], mod_times) is False

    def test_new_file_detected(self, app, tmp_path):
        """新增文件返回 True"""
        mod_times = app._scan_file_modtimes([str(tmp_path)])
        (tmp_path / 'new.py').write_text('x = 1')
        assert app._check_file_changes([str(tmp_path)], mod_times) is True

    def test_modified_file_detected(self, app, tmp_path):
        """修改文件返回 True"""
        f = tmp_path / 'a.py'
        f.write_text('x = 1')
        mod_times = app._scan_file_modtimes([str(tmp_path)])
        f.write_text('x = 2')
        assert app._check_file_changes([str(tmp_path)], mod_times) is True

    def test_deleted_file_detected(self, app, tmp_path):
        """删除文件返回 True"""
        f = tmp_path / 'a.py'
        f.write_text('x = 1')
        mod_times = app._scan_file_modtimes([str(tmp_path)])
        f.unlink()
        assert app._check_file_changes([str(tmp_path)], mod_times) is True


class TestRunWithReload:
    """热重载主循环测试"""

    def test_child_exit_nonzero_breaks_loop(self, app, restore_signals, no_sleep):
        """子进程异常退出（非 0/-2/-15）记录错误并终止"""
        child = make_child(1, [1, 1])
        with patch('subprocess.Popen', return_value=child) as popen:
            app._run_with_reload(None)
        popen.assert_called_once()

    def test_child_exit_zero_restarts(self, app, restore_signals, no_sleep):
        """子进程正常退出（0）后重启新一轮"""
        child1 = make_child(0, [0, 0])
        child2 = make_child(1, [1, 1])
        with patch('subprocess.Popen', side_effect=[child1, child2]):
            app._run_with_reload(None)

    def test_popen_error_retries(self, app, restore_signals, no_sleep):
        """启动失败记录错误后重试"""
        child = make_child(1, [1, 1])
        with patch('subprocess.Popen',
                   side_effect=[OSError('boom'), child]) as popen:
            app._run_with_reload(None)
        assert popen.call_count == 2

    def test_file_change_restarts_child(self, app, restore_signals, no_sleep,
                                        tmp_path):
        """文件变化时终止子进程并重启"""
        main_file = tmp_path / 'main.py'
        main_file.write_text('print()')
        child1 = make_child(None, [None, 1])
        child2 = make_child(1, [1, 1])
        app._check_file_changes = Mock(return_value=True)
        with patch('subprocess.Popen', side_effect=[child1, child2]):
            app._run_with_reload(str(main_file))
        child1.terminate.assert_called_once()

    def test_terminate_timeout_kills_child(self, app, restore_signals, no_sleep,
                                           tmp_path):
        """终止超时升级为 kill"""
        main_file = tmp_path / 'main.py'
        main_file.write_text('print()')
        child1 = make_child(None, [None, 1])
        child1.wait.side_effect = [subprocess.TimeoutExpired('cmd', 5), 0]
        child2 = make_child(1, [1, 1])
        app._check_file_changes = Mock(return_value=True)
        with patch('subprocess.Popen', side_effect=[child1, child2]):
            app._run_with_reload(str(main_file))
        child1.kill.assert_called_once()

    def test_watch_dirs_include_src(self, app, restore_signals, no_sleep,
                                    tmp_path):
        """main_file 旁存在 src 目录时一并纳入监视"""
        main_file = tmp_path / 'app' / 'main.py'
        main_file.parent.mkdir()
        main_file.write_text('print()')
        src_dir = tmp_path / 'src'
        src_dir.mkdir()
        (src_dir / 'mod.py').write_text('x = 1')

        scanned = []
        original_scan = app._scan_file_modtimes

        def tracking_scan(watch_dirs):
            scanned.append(list(watch_dirs))
            return original_scan(watch_dirs)

        app._scan_file_modtimes = tracking_scan
        child = make_child(1, [1, 1])
        with patch('subprocess.Popen', return_value=child):
            app._run_with_reload(str(main_file))
        assert scanned[0] == [str(main_file.parent), str(src_dir)]

    def test_parent_signal_handler_exits(self, app, restore_signals, no_sleep):
        """父进程信号处理器在子进程已退出时直接退出"""
        child = make_child(1, [1, 1, 1])
        with patch('subprocess.Popen', return_value=child):
            app._run_with_reload(None)

        handler = signal.getsignal(signal.SIGTERM)
        with pytest.raises(SystemExit):
            handler(signal.SIGTERM, None)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
