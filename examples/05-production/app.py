#!/usr/bin/env python3
"""
Litefs 生产环境部署示例

本示例演示:
1. 多进程模式 - workers 参数启动多进程
2. 日志配置 - 结构化日志输出到文件
3. 缓存系统 - 内存/Redis 缓存
4. 健康检查 - 用于负载均衡器的健康检查端点
5. Debug 工具 - 环境变量控制的调试工具栏
6. 优雅关闭 - 正确处理进程信号

启动方式:
    开发模式: python app.py
    生产模式: WORKERS=4 python app.py
    启用调试: DEBUG_TOOLBAR=true python app.py
"""

import os
import sys
import signal
import logging
import logging.handlers
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs, Response
from litefs.routing import get, post
from litefs.middleware.logging import LoggingMiddleware
from litefs.middleware.csrf import CSRFMiddleware
from litefs.cache import MemoryCache
from litefs.debug import DebugMiddleware

APP_DIR = os.path.dirname(os.path.abspath(__file__))

debug_mode = os.environ.get('DEBUG', 'false').lower() == 'true'
debug_toolbar = os.environ.get('DEBUG_TOOLBAR', 'false').lower() == 'true'
workers = int(os.environ.get('WORKERS', '1'))
secret_key = os.environ.get('SECRET_KEY', 'production-secret-key-change-me')


def setup_logging(app: Litefs) -> None:
    log_dir = os.path.join(APP_DIR, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(log_format)

    file_handler = logging.handlers.RotatingFileHandler(
        os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if debug_mode else logging.INFO)

    app_logger = logging.getLogger('litefs')
    app_logger.setLevel(logging.DEBUG)
    app_logger.addHandler(file_handler)
    app_logger.addHandler(console_handler)


app = Litefs(
    host='0.0.0.0',
    port=8085,
    debug=debug_mode,
    workers=workers,
    secret_key=secret_key
)

app.add_static('/static', os.path.join(APP_DIR, 'static'))

setup_logging(app)

app.add_middleware(LoggingMiddleware)

if not debug_mode:
    app.add_middleware(CSRFMiddleware)

if debug_toolbar:
    app.add_middleware(DebugMiddleware)

try:
    from litefs.cache import RedisCache
    app.cache = RedisCache(
        host=os.environ.get('REDIS_HOST', 'localhost'),
        port=int(os.environ.get('REDIS_PORT', 6379)),
        db=int(os.environ.get('REDIS_DB', 0)),
        key_prefix='litefs:'
    )
    app.logger.info("Redis 缓存已连接")
except Exception as e:
    app.logger.warning(f"Redis 连接失败，使用内存缓存: {e}")
    app.cache = MemoryCache()


class HealthStatus:
    def __init__(self):
        self.start_time = datetime.now()
        self.requests_count = 0
        self.errors_count = 0

    @property
    def uptime(self) -> str:
        delta = datetime.now() - self.start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours}h {minutes}m {seconds}s"


health_status = HealthStatus()


@get('/', name='index')
def index(request):
    health_status.requests_count += 1

    data = {
        'message': 'Litefs 生产环境示例',
        'features': [
            '多进程模式',
            '结构化日志',
            'Redis 缓存',
            '健康检查端点',
            '优雅关闭'
        ],
        'workers': workers,
        'debug': debug_mode,
        'uptime': health_status.uptime
    }

    return request.render_template('index.html', **data)


@get('/health', name='health')
def health_check(request):
    return Response.json({
        'status': 'healthy',
        'uptime': health_status.uptime,
        'requests': health_status.requests_count,
        'errors': health_status.errors_count,
        'workers': workers,
        'timestamp': datetime.now().isoformat()
    })


@get('/ready', name='ready')
def readiness_check(request):
    checks = {
        'server': True,
        'cache': False,
    }

    try:
        app.cache.put('health_check', 'ok')
        if app.cache.get('health_check') == 'ok':
            checks['cache'] = True
    except Exception:
        pass

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return Response.json({
        'ready': all_healthy,
        'checks': checks
    }, status_code=status_code)


@get('/metrics', name='metrics')
def metrics(request):
    return Response.json({
        'uptime_seconds': (datetime.now() - health_status.start_time).total_seconds(),
        'requests_total': health_status.requests_count,
        'errors_total': health_status.errors_count,
        'workers': workers,
    })


@post('/api/cache/clear', name='cache_clear')
def clear_cache(request):
    try:
        app.cache._cache.clear()
        return Response.json({'success': True, 'message': '缓存已清除'})
    except Exception as e:
        health_status.errors_count += 1
        return Response.json({'success': False, 'error': str(e)}, status_code=500)


@get('/api/config', name='config')
def get_config(request):
    return Response.json({
        'workers': workers,
        'debug': debug_mode,
        'log_level': 'DEBUG' if debug_mode else 'INFO'
    })


app.register_routes(__name__)


def signal_handler(signum, frame):
    app.logger.info(f"收到信号 {signum}，正在优雅关闭...")
    sys.exit(0)


signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)


if __name__ == '__main__':
    app.logger.info(f"启动 Litefs 生产服务器，workers={workers}")
    app.run()
