#!/usr/bin/env python
# coding: utf-8

"""
调试工具模块

提供开发调试功能：
- 请求/响应检查器
- SQL 查询日志
- 性能分析器
- 错误追踪面板

启用方式：
    export LITEFS_DEBUG=1
    python app.py
"""

import os
import time
import sys
from typing import Dict, List, Any, Optional
from contextvars import ContextVar
from dataclasses import dataclass, field


_current_request_debug: ContextVar[Optional['RequestDebug']] = ContextVar('current_request_debug', default=None)


def is_debug_enabled() -> bool:
    """检查是否启用调试模式"""
    return os.environ.get('LITEFS_DEBUG', '0') == '1'


def get_current_debug() -> Optional['RequestDebug']:
    """获取当前请求的调试信息"""
    return _current_request_debug.get()


@dataclass
class SQLQuery:
    """SQL 查询记录"""
    sql: str
    params: tuple = ()
    duration: float = 0.0
    timestamp: float = field(default_factory=time.time)
    
    def __str__(self):
        if self.params:
            return f"{self.sql} | params: {self.params}"
        return self.sql


@dataclass
class RequestDebug:
    """请求调试信息"""
    request_id: int
    method: str = ''
    path: str = ''
    query_string: str = ''
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    session: Dict[str, Any] = field(default_factory=dict)
    body: str = ''
    
    start_time: float = field(default_factory=time.time)
    end_time: float = 0.0
    
    routing_time: float = 0.0
    handler_time: float = 0.0
    db_time: float = 0.0
    template_time: float = 0.0
    
    sql_queries: List[SQLQuery] = field(default_factory=list)
    
    response_status: int = 0
    response_headers: Dict[str, str] = field(default_factory=dict)
    response_size: int = 0
    
    errors: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_sql_query(self, sql: str, params: tuple = (), duration: float = 0.0):
        """添加 SQL 查询记录"""
        query = SQLQuery(sql=sql, params=params, duration=duration)
        self.sql_queries.append(query)
        self.db_time += duration
    
    def add_error(self, error: Exception, context: str = ''):
        """添加错误记录"""
        import traceback
        self.errors.append({
            'type': type(error).__name__,
            'message': str(error),
            'traceback': traceback.format_exc(),
            'context': context,
            'timestamp': time.time(),
        })
    
    @property
    def total_time(self) -> float:
        """总耗时（毫秒）"""
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000
    
    def finish(self):
        """标记请求结束"""
        self.end_time = time.time()


class DebugToolbar:
    """
    调试工具栏
    
    协调各调试面板，收集和输出调试信息。
    """
    
    _request_counter = 0
    
    def __init__(self):
        self.enabled = is_debug_enabled()
    
    @classmethod
    def start_request(cls, method: str, path: str, query_string: str = '') -> RequestDebug:
        """开始请求调试"""
        cls._request_counter += 1
        
        debug = RequestDebug(
            request_id=cls._request_counter,
            method=method,
            path=path,
            query_string=query_string,
        )
        
        _current_request_debug.set(debug)
        return debug
    
    @classmethod
    def end_request(cls, debug: RequestDebug):
        """结束请求调试"""
        debug.finish()
        _current_request_debug.set(None)
        
        if is_debug_enabled():
            cls._output(debug)
    
    @staticmethod
    def _output(debug: RequestDebug):
        """输出调试信息到终端"""
        formatter = TerminalFormatter()
        formatter.output(debug)


class TerminalFormatter:
    """终端格式化输出"""
    
    COLORS = {
        'red': '\033[91m',
        'green': '\033[92m',
        'yellow': '\033[93m',
        'blue': '\033[94m',
        'magenta': '\033[95m',
        'cyan': '\033[96m',
        'white': '\033[97m',
        'gray': '\033[90m',
        'reset': '\033[0m',
        'bold': '\033[1m',
    }
    
    def color(self, text: str, color: str) -> str:
        """添加颜色"""
        code = self.COLORS.get(color, '')
        reset = self.COLORS['reset'] if code else ''
        return f"{code}{text}{reset}"
    
    def box(self, lines: List[str]) -> str:
        """创建边框盒子"""
        max_width = max(len(line) for line in lines) if lines else 60
        max_width = max(max_width, 60)
        
        result = [f"┌{'─' * (max_width + 2)}┐"]
        for line in lines:
            result.append(f"│ {line.ljust(max_width)} │")
        result.append(f"└{'─' * (max_width + 2)}┘")
        return '\n'.join(result)
    
    def separator(self, char: str = '═', width: int = 65) -> str:
        """分隔线"""
        return char * width
    
    def output(self, debug: RequestDebug):
        """输出调试信息"""
        lines = []
        
        lines.append('')
        lines.append(self.color(self.separator(), 'cyan'))
        lines.append(self.color(f"🔍 Litefs Debug - Request #{debug.request_id}", 'cyan'))
        lines.append(self.color(self.separator(), 'cyan'))
        lines.append('')
        
        lines.append(self.color('📌 Request', 'blue'))
        request_lines = self._format_request(debug)
        lines.append(self.box(request_lines))
        lines.append('')
        
        lines.append(self.color('⏱️  Performance', 'blue'))
        perf_lines = self._format_performance(debug)
        lines.append(self.box(perf_lines))
        lines.append('')
        
        if debug.sql_queries:
            lines.append(self.color(f'💾 SQL Queries ({len(debug.sql_queries)})', 'blue'))
            sql_lines = self._format_sql(debug)
            lines.append(self.box(sql_lines))
            lines.append('')
        
        if debug.errors:
            lines.append(self.color(f'❌ Errors ({len(debug.errors)})', 'red'))
            error_lines = self._format_errors(debug)
            lines.append(self.box(error_lines))
            lines.append('')
        
        lines.append(self.color('📤 Response', 'blue'))
        response_lines = self._format_response(debug)
        lines.append(self.box(response_lines))
        lines.append('')
        
        lines.append(self.color(self.separator(), 'cyan'))
        lines.append('')
        
        print('\n'.join(lines), file=sys.stderr)
    
    def _format_request(self, debug: RequestDebug) -> List[str]:
        """格式化请求信息"""
        lines = []
        
        url = debug.path
        if debug.query_string:
            url += f'?{debug.query_string}'
        lines.append(f"{self.color(debug.method, 'green')} {url}")
        
        for key, value in debug.headers.items():
            if key.lower() in ('cookie', 'authorization'):
                value = self._mask_sensitive(value)
            lines.append(f"{key}: {value}")
        
        if debug.cookies:
            lines.append(f"Cookies: {', '.join(debug.cookies.keys())}")
        
        if debug.body:
            body_preview = debug.body[:200] + '...' if len(debug.body) > 200 else debug.body
            lines.append(f"Body: {body_preview}")
        
        return lines
    
    def _format_performance(self, debug: RequestDebug) -> List[str]:
        """格式化性能信息"""
        lines = []
        
        total = debug.total_time
        lines.append(f"Total:     {total:8.2f}ms")
        lines.append(f"Routing:   {debug.routing_time:8.2f}ms")
        lines.append(f"Handler:   {debug.handler_time:8.2f}ms")
        
        db_line = f"DB:        {debug.db_time:8.2f}ms ({len(debug.sql_queries)} queries)"
        if debug.db_time > 100:
            db_line = self.color(db_line, 'yellow')
        lines.append(db_line)
        
        lines.append(f"Template:  {debug.template_time:8.2f}ms")
        
        return lines
    
    def _format_sql(self, debug: RequestDebug) -> List[str]:
        """格式化 SQL 查询"""
        lines = []
        slow_threshold = 10.0
        
        for i, query in enumerate(debug.sql_queries, 1):
            sql_preview = query.sql[:60] + '...' if len(query.sql) > 60 else query.sql
            duration_str = f"{query.duration:6.2f}ms"
            
            if query.duration > slow_threshold:
                duration_str = self.color(duration_str, 'yellow')
            
            lines.append(f"[{i}] {duration_str}  {sql_preview}")
        
        slow_queries = [q for q in debug.sql_queries if q.duration > slow_threshold]
        if slow_queries:
            lines.append('')
            for q in slow_queries:
                lines.append(self.color(f"⚠️  Slow Query: {q.sql[:50]}... ({q.duration:.2f}ms)", 'yellow'))
        
        return lines
    
    def _format_errors(self, debug: RequestDebug) -> List[str]:
        """格式化错误信息"""
        lines = []
        
        for error in debug.errors:
            lines.append(self.color(f"{error['type']}: {error['message']}", 'red'))
            if error['context']:
                lines.append(f"Context: {error['context']}")
        
        return lines
    
    def _format_response(self, debug: RequestDebug) -> List[str]:
        """格式化响应信息"""
        lines = []
        
        status_color = 'green' if 200 <= debug.response_status < 300 else 'yellow' if 300 <= debug.response_status < 400 else 'red'
        lines.append(f"Status: {self.color(str(debug.response_status), status_color)}")
        
        content_type = debug.response_headers.get('Content-Type', 'unknown')
        lines.append(f"Content-Type: {content_type}")
        
        size_str = self._format_size(debug.response_size)
        lines.append(f"Size: {size_str}")
        
        return lines
    
    def _format_size(self, size: int) -> str:
        """格式化文件大小"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}TB"
    
    def _mask_sensitive(self, value: str) -> str:
        """遮蔽敏感信息"""
        if len(value) > 10:
            return value[:5] + '***' + value[-5:]
        return '***'


toolbar = DebugToolbar()

from .middleware import DebugMiddleware, track_sql, track_performance

__all__ = [
    'is_debug_enabled',
    'get_current_debug',
    'SQLQuery',
    'RequestDebug',
    'DebugToolbar',
    'TerminalFormatter',
    'toolbar',
    'DebugMiddleware',
    'track_sql',
    'track_performance',
]
