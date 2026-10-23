#!/usr/bin/env python
# coding: utf-8

"""
调试中间件与调试工具模块测试

覆盖 litefs.debug.__init__（RequestDebug / DebugToolbar / TerminalFormatter）
与 litefs.debug.middleware（DebugMiddleware / track_sql / track_performance）。
"""

import io
import json
import os
import unittest
from contextlib import redirect_stderr
from unittest.mock import Mock, patch

from litefs import debug as debug_module
from litefs.debug import (
    DebugToolbar,
    RequestDebug,
    SQLQuery,
    TerminalFormatter,
    get_current_debug,
    is_debug_enabled,
)
from litefs.debug.middleware import DebugMiddleware, track_performance, track_sql


def make_handler(environ=None):
    """构造一个仅声明 environ 属性的请求处理器 Mock"""
    handler = Mock(spec=[])
    handler.environ = environ if environ is not None else {}
    return handler


class DebugTestCase(unittest.TestCase):
    """公共基类：重置 ContextVar 与请求计数器，避免测试间状态污染"""

    def setUp(self):
        debug_module._current_request_debug.set(None)
        DebugToolbar._request_counter = 0

    def tearDown(self):
        debug_module._current_request_debug.set(None)
        DebugToolbar._request_counter = 0


class TestIsDebugEnabled(DebugTestCase):
    """is_debug_enabled 环境变量开关"""

    def test_enabled_when_env_is_1(self):
        """LITEFS_DEBUG=1 时启用调试"""
        with patch.dict(os.environ, {'LITEFS_DEBUG': '1'}):
            self.assertTrue(is_debug_enabled())

    def test_disabled_by_default(self):
        """未设置环境变量时默认关闭"""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop('LITEFS_DEBUG', None)
            self.assertFalse(is_debug_enabled())

    def test_disabled_with_other_values(self):
        """LITEFS_DEBUG 为非 1 值时关闭"""
        with patch.dict(os.environ, {'LITEFS_DEBUG': 'yes'}):
            self.assertFalse(is_debug_enabled())


class TestSQLQuery(DebugTestCase):
    """SQLQuery 数据类"""

    def test_str_without_params(self):
        """无参数时直接返回 SQL"""
        query = SQLQuery(sql='SELECT 1')
        self.assertEqual(str(query), 'SELECT 1')

    def test_str_with_params(self):
        """有参数时附带参数信息"""
        query = SQLQuery(sql='SELECT * FROM t WHERE id=?', params=(1,))
        self.assertEqual(str(query), 'SELECT * FROM t WHERE id=? | params: (1,)')


class TestRequestDebug(DebugTestCase):
    """RequestDebug 请求调试信息"""

    def test_add_sql_query(self):
        """添加 SQL 查询会追加记录并累计 db_time"""
        debug = RequestDebug(request_id=1)
        debug.add_sql_query('SELECT 1', (1,), duration=5.0)
        debug.add_sql_query('SELECT 2', duration=10.0)
        self.assertEqual(len(debug.sql_queries), 2)
        self.assertAlmostEqual(debug.db_time, 15.0)
        self.assertEqual(debug.sql_queries[0].sql, 'SELECT 1')

    def test_add_error(self):
        """添加错误会记录类型、消息、上下文与时间戳"""
        debug = RequestDebug(request_id=1)
        try:
            raise ValueError('boom')
        except ValueError as exc:
            debug.add_error(exc, context='Request handler')

        self.assertEqual(len(debug.errors), 1)
        entry = debug.errors[0]
        self.assertEqual(entry['type'], 'ValueError')
        self.assertEqual(entry['message'], 'boom')
        self.assertEqual(entry['context'], 'Request handler')
        self.assertIn('Traceback', entry['traceback'])
        self.assertGreater(entry['timestamp'], 0)

    def test_total_time_before_finish(self):
        """未结束时总耗时为当前时间与开始时间的差"""
        debug = RequestDebug(request_id=1)
        debug.start_time -= 1.0
        self.assertGreater(debug.total_time, 900.0)

    def test_total_time_after_finish(self):
        """结束后总耗时由 end_time 决定"""
        debug = RequestDebug(request_id=1)
        debug.start_time = 100.0
        debug.end_time = 101.0
        self.assertAlmostEqual(debug.total_time, 1000.0)

    def test_finish_sets_end_time(self):
        """finish 标记请求结束"""
        debug = RequestDebug(request_id=1)
        self.assertEqual(debug.end_time, 0.0)
        debug.finish()
        self.assertGreater(debug.end_time, 0)


class TestDebugToolbar(DebugTestCase):
    """DebugToolbar 请求调试协调器"""

    def test_start_request_creates_debug(self):
        """start_request 创建调试对象并写入上下文"""
        debug = DebugToolbar.start_request('GET', '/index', 'a=1')
        self.assertIsInstance(debug, RequestDebug)
        self.assertEqual(debug.method, 'GET')
        self.assertEqual(debug.path, '/index')
        self.assertEqual(debug.query_string, 'a=1')
        self.assertEqual(debug.request_id, 1)
        self.assertIs(get_current_debug(), debug)

        second = DebugToolbar.start_request('POST', '/submit')
        self.assertEqual(second.request_id, 2)

    def test_end_request_finishes_and_clears_context(self):
        """end_request 标记结束并清空上下文"""
        debug = DebugToolbar.start_request('GET', '/index')
        DebugToolbar.end_request(debug)
        self.assertGreater(debug.end_time, 0)
        self.assertIsNone(get_current_debug())

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    @patch.object(DebugToolbar, '_output')
    def test_end_request_outputs_when_enabled(self, mock_output):
        """调试启用时 end_request 输出调试面板"""
        debug = DebugToolbar.start_request('GET', '/index')
        DebugToolbar.end_request(debug)
        mock_output.assert_called_once_with(debug)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '0'})
    @patch.object(DebugToolbar, '_output')
    def test_end_request_no_output_when_disabled(self, mock_output):
        """调试关闭时 end_request 不输出"""
        debug = DebugToolbar.start_request('GET', '/index')
        DebugToolbar.end_request(debug)
        mock_output.assert_not_called()


class TestTerminalFormatter(DebugTestCase):
    """TerminalFormatter 终端格式化输出"""

    def setUp(self):
        super().setUp()
        self.formatter = TerminalFormatter()

    def test_color_known_and_unknown(self):
        """已知颜色添加 ANSI 代码，未知颜色原样返回"""
        colored = self.formatter.color('ok', 'green')
        self.assertIn('\033[92m', colored)
        self.assertIn('\033[0m', colored)
        self.assertEqual(self.formatter.color('ok', 'invalid'), 'ok')

    def test_box(self):
        """box 为内容行添加边框"""
        result = self.formatter.box(['hello'])
        self.assertTrue(result.startswith('┌'))
        self.assertIn('hello', result)
        self.assertTrue(result.rstrip().endswith('┘'))

    def test_box_empty_lines(self):
        """空内容时使用默认宽度 60"""
        result = self.formatter.box([])
        self.assertIn('┌', result)
        for line in result.splitlines()[1:-1]:
            self.assertIn(' ', line)
            self.assertGreaterEqual(len(line), 60)

    def test_separator(self):
        """separator 按指定字符与宽度生成"""
        self.assertEqual(self.formatter.separator('═', 10), '═' * 10)
        self.assertEqual(len(self.formatter.separator()), 65)

    def test_output_prints_to_stderr(self):
        """output 输出调试面板到 stderr"""
        debug = RequestDebug(request_id=7, method='GET', path='/x')
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            self.formatter.output(debug)
        content = buffer.getvalue()
        self.assertIn('Request #7', content)
        self.assertIn('Performance', content)
        self.assertIn('Response', content)

    def test_format_request_with_query_string(self):
        """带查询字符串时输出完整 URL"""
        debug = RequestDebug(request_id=1, method='GET', path='/search', query_string='q=abc')
        lines = self.formatter._format_request(debug)
        self.assertIn('/search?q=abc', lines[0])

    def test_format_request_masks_sensitive_headers(self):
        """Cookie 与 Authorization 头被遮蔽"""
        debug = RequestDebug(request_id=1, method='GET', path='/')
        debug.headers = {
            'Authorization': 'Bearer super-secret-token-value',
            'Accept': 'text/html',
        }
        lines = self.formatter._format_request(debug)
        self.assertIn('Authorization: Beare***value', lines)
        self.assertIn('Accept: text/html', lines)
        self.assertNotIn('super-secret-token-value', '\n'.join(lines))

    def test_format_request_cookies_and_body(self):
        """输出 Cookie 键名与 Body 预览，超长 Body 截断"""
        debug = RequestDebug(request_id=1, method='POST', path='/')
        debug.cookies = {'session': 'abc'}
        debug.body = 'x' * 300
        lines = self.formatter._format_request(debug)
        self.assertIn('Cookies: session', lines)
        body_line = next(line for line in lines if line.startswith('Body:'))
        self.assertIn('...', body_line)
        self.assertEqual(len(body_line), len('Body: ') + 200 + 3)

    def test_format_performance_slow_db_highlighted(self):
        """DB 耗时超过 100ms 时高亮显示"""
        debug = RequestDebug(request_id=1)
        debug.db_time = 150.0
        lines = self.formatter._format_performance(debug)
        db_line = next(line for line in lines if 'DB:' in line)
        self.assertIn('\033[93m', db_line)
        self.assertIn('150.00ms', db_line)

    def test_format_sql_with_slow_query(self):
        """慢查询显示高亮时长与警告"""
        debug = RequestDebug(request_id=1)
        debug.add_sql_query('SELECT * FROM users WHERE id = 1', duration=25.0)
        debug.add_sql_query('SELECT 1', duration=1.0)
        lines = self.formatter._format_sql(debug)
        content = '\n'.join(lines)
        self.assertIn('Slow Query', content)
        self.assertIn('25.00ms', content)
        self.assertIn('1.00ms', content)

    def test_format_errors(self):
        """错误面板包含类型、消息与上下文"""
        debug = RequestDebug(request_id=1)
        debug.errors.append({
            'type': 'ValueError', 'message': 'boom',
            'context': 'Request handler', 'timestamp': 0, 'traceback': '',
        })
        lines = self.formatter._format_errors(debug)
        self.assertIn('ValueError: boom', lines[0])
        self.assertIn('Context: Request handler', lines[1])

    def test_format_response_status_colors(self):
        """状态码按区间着色：2xx 绿、3xx 黄、其余红"""
        for status, color_code in ((200, '\033[92m'), (301, '\033[93m'), (500, '\033[91m')):
            debug = RequestDebug(request_id=1)
            debug.response_status = status
            lines = self.formatter._format_response(debug)
            self.assertIn(f'Status: {color_code}{status}', lines[0])

    def test_format_size_units(self):
        """文件大小按 B/KB/MB/GB/TB 格式化"""
        self.assertEqual(self.formatter._format_size(500), '500.0B')
        self.assertEqual(self.formatter._format_size(2048), '2.0KB')
        self.assertEqual(self.formatter._format_size(1024 ** 2), '1.0MB')
        self.assertEqual(self.formatter._format_size(1024 ** 3), '1.0GB')
        self.assertEqual(self.formatter._format_size(1024 ** 4), '1.0TB')

    def test_mask_sensitive(self):
        """长值保留首尾各 5 字符，短值完全遮蔽"""
        self.assertEqual(self.formatter._mask_sensitive('abcdefghijk'), 'abcde***ghijk')
        self.assertEqual(self.formatter._mask_sensitive('short'), '***')


class TestDebugMiddleware(DebugTestCase):
    """DebugMiddleware 调试中间件"""

    def _make_middleware(self):
        return DebugMiddleware(app=Mock())

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_init_reads_env(self):
        """初始化时读取 LITEFS_DEBUG 决定启用状态"""
        self.assertTrue(self._make_middleware().enabled)
        with patch.dict(os.environ, {'LITEFS_DEBUG': '0'}):
            self.assertFalse(self._make_middleware().enabled)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '0'})
    def test_process_request_disabled(self):
        """未启用时 process_request 直接跳过"""
        middleware = self._make_middleware()
        handler = make_handler({'REQUEST_METHOD': 'GET'})
        self.assertIsNone(middleware.process_request(handler))
        self.assertFalse(hasattr(handler, '_debug'))

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_request_collects_headers(self):
        """启用时收集 HTTP_* 头并转换命名"""
        middleware = self._make_middleware()
        handler = make_handler({
            'REQUEST_METHOD': 'POST',
            'PATH_INFO': '/submit',
            'QUERY_STRING': 'a=1',
            'HTTP_USER_AGENT': 'test-agent',
            'HTTP_ACCEPT_ENCODING': 'gzip',
            'CONTENT_TYPE': 'application/json',
        })
        middleware.process_request(handler)

        debug = handler._debug
        self.assertEqual(debug.method, 'POST')
        self.assertEqual(debug.path, '/submit')
        self.assertEqual(debug.query_string, 'a=1')
        self.assertEqual(debug.headers, {'User-Agent': 'test-agent', 'Accept-Encoding': 'gzip'})
        self.assertIs(get_current_debug(), debug)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_request_defaults(self):
        """environ 缺失时使用默认 method/path"""
        middleware = self._make_middleware()
        handler = make_handler({})
        middleware.process_request(handler)
        debug = handler._debug
        self.assertEqual(debug.method, 'GET')
        self.assertEqual(debug.path, '/')
        self.assertEqual(debug.headers, {})

    @patch.dict(os.environ, {'LITEFS_DEBUG': '0'})
    def test_process_response_disabled(self):
        """未启用时响应原样返回"""
        middleware = self._make_middleware()
        handler = make_handler()
        response = ('200 OK', [], b'data')
        self.assertEqual(middleware.process_response(handler, response), response)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_response_without_debug(self):
        """无 _debug 属性时响应原样返回"""
        middleware = self._make_middleware()
        handler = make_handler()
        response = ('200 OK', [], b'data')
        self.assertEqual(middleware.process_response(handler, response), response)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_response_tuple_branch(self):
        """三元组响应：解析状态行、响应头与字节数"""
        middleware = self._make_middleware()
        handler = make_handler()
        middleware.process_request(handler)
        debug = handler._debug
        debug.start_time -= 0.01

        response = ('200 OK', [('Content-Type', 'text/plain')], b'hello')
        result = middleware.process_response(handler, response)

        self.assertEqual(result, response)
        self.assertEqual(debug.response_status, 200)
        self.assertEqual(debug.response_headers, {'Content-Type': 'text/plain'})
        self.assertEqual(debug.response_size, 5)
        self.assertGreater(debug.handler_time, 0)
        self.assertGreater(debug.end_time, 0)
        self.assertIsNone(get_current_debug())

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_response_tuple_str_body(self):
        """三元组响应：字符串 body 按 UTF-8 计算字节数"""
        middleware = self._make_middleware()
        handler = make_handler()
        middleware.process_request(handler)
        debug = handler._debug

        middleware.process_response(handler, ('200 OK', [], '你好'))
        self.assertEqual(debug.response_size, 6)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_response_tuple_non_numeric_status(self):
        """状态行首段非数字时不解析状态码"""
        middleware = self._make_middleware()
        handler = make_handler()
        middleware.process_request(handler)
        debug = handler._debug

        middleware.process_response(handler, ('OK', [], b'x'))
        self.assertEqual(debug.response_status, 0)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_response_dict_branch_with_handler_attrs(self):
        """非三元组响应：从 handler 属性读取状态码与响应头"""
        middleware = self._make_middleware()
        handler = make_handler()
        middleware.process_request(handler)
        debug = handler._debug
        handler._status_code = 201
        handler._response_headers = {'X-Foo': 'bar'}

        response = 'plain text'
        result = middleware.process_response(handler, response)

        self.assertEqual(result, response)
        self.assertEqual(debug.response_status, 201)
        self.assertEqual(debug.response_headers, {'X-Foo': 'bar'})
        self.assertEqual(debug.response_size, len('plain text'))

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_response_dict_json_size(self):
        """非三元组响应：dict/list 按 JSON 序列化计算字节数"""
        middleware = self._make_middleware()
        handler = make_handler()
        middleware.process_request(handler)
        debug = handler._debug

        response = {'message': 'ok', '中文': '数据'}
        middleware.process_response(handler, response)
        # 与框架统一的 JSON 编码器保持一致，避免绑定到具体序列化器的分隔符风格
        from litefs._json import dumps
        expected = len(dumps(response))
        self.assertEqual(debug.response_size, expected)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_response_without_handler_attrs(self):
        """handler 无状态属性且响应为空时保持默认值"""
        middleware = self._make_middleware()
        handler = make_handler()
        middleware.process_request(handler)
        debug = handler._debug

        middleware.process_response(handler, '')
        self.assertEqual(debug.response_status, 0)
        self.assertEqual(debug.response_headers, {})
        self.assertEqual(debug.response_size, 0)

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_exception_records_error(self):
        """异常处理记录错误及上下文"""
        middleware = self._make_middleware()
        handler = make_handler()
        middleware.process_request(handler)
        debug = handler._debug

        middleware.process_exception(handler, RuntimeError('handler failed'))
        self.assertEqual(len(debug.errors), 1)
        self.assertEqual(debug.errors[0]['type'], 'RuntimeError')
        self.assertEqual(debug.errors[0]['context'], 'Request handler')

    @patch.dict(os.environ, {'LITEFS_DEBUG': '0'})
    def test_process_exception_disabled(self):
        """未启用时异常处理直接跳过"""
        middleware = self._make_middleware()
        handler = make_handler()
        self.assertIsNone(middleware.process_exception(handler, RuntimeError('x')))

    @patch.dict(os.environ, {'LITEFS_DEBUG': '1'})
    def test_process_exception_without_debug(self):
        """无 _debug 属性时异常处理不崩溃"""
        middleware = self._make_middleware()
        handler = make_handler()
        self.assertIsNone(middleware.process_exception(handler, RuntimeError('x')))


class TestTrackSQL(DebugTestCase):
    """track_sql SQL 追踪上下文管理器"""

    def test_records_query_with_duration(self):
        """退出时记录 SQL 及耗时并累计 db_time"""
        debug = DebugToolbar.start_request('GET', '/db')
        with track_sql('SELECT * FROM users WHERE id=?', (1,)):
            pass
        self.assertEqual(len(debug.sql_queries), 1)
        query = debug.sql_queries[0]
        self.assertEqual(query.sql, 'SELECT * FROM users WHERE id=?')
        self.assertEqual(query.params, (1,))
        self.assertGreaterEqual(query.duration, 0)
        self.assertGreaterEqual(debug.db_time, 0)

    def test_without_current_debug(self):
        """无当前调试对象时不崩溃"""
        with track_sql('SELECT 1'):
            pass
        self.assertIsNone(get_current_debug())


class TestTrackPerformance(DebugTestCase):
    """track_performance 性能追踪上下文管理器"""

    def test_routing_time(self):
        """routing 名称累计到 routing_time"""
        debug = DebugToolbar.start_request('GET', '/route')
        with track_performance('routing'):
            pass
        self.assertGreaterEqual(debug.routing_time, 0)
        self.assertEqual(debug.template_time, 0)

    def test_template_time(self):
        """template 名称累计到 template_time"""
        debug = DebugToolbar.start_request('GET', '/render')
        with track_performance('template'):
            pass
        self.assertGreaterEqual(debug.template_time, 0)
        self.assertEqual(debug.routing_time, 0)

    def test_other_name_ignored(self):
        """其他名称不累计任何指标"""
        debug = DebugToolbar.start_request('GET', '/other')
        with track_performance('custom'):
            pass
        self.assertEqual(debug.routing_time, 0)
        self.assertEqual(debug.template_time, 0)

    def test_without_current_debug(self):
        """无当前调试对象时不崩溃"""
        with track_performance('routing'):
            pass
        self.assertIsNone(get_current_debug())


if __name__ == '__main__':
    unittest.main()
