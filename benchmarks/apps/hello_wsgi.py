"""Hello World 应用 - WSGI 模式"""

import sys
import os
import argparse
import logging

# 禁用所有日志输出
logging.disable(logging.CRITICAL)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs.core import Litefs
from litefs.routing import get


DEFAULT_PORT = 8080

app = Litefs(host="0.0.0.0", port=DEFAULT_PORT)


@get("/")
def index(request):
    return "Hello World"


@get("/health")
def health(request):
    return {"status": "ok"}


app.register_routes(__name__)

# WSGI 应用入口
application = app.wsgi()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Hello World LiteFS WSGI Server')
    parser.add_argument('--port', '-P', type=int, default=DEFAULT_PORT, help='Port to listen on')
    parser.add_argument('--host', '-H', type=str, default='0.0.0.0', help='Host to bind to')
    args = parser.parse_args()
    
    app.host = args.host
    app.port = args.port
    
    workers = int(os.environ.get("WORKERS", 1))
    app.run(processes=workers)
