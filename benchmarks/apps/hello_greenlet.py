"""Hello World 应用 - 原生 HTTP 服务器 (使用 epoll + greenlet)"""

import sys
import os
import logging

# 禁用所有日志输出
logging.disable(logging.CRITICAL)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get

app = Litefs(host="0.0.0.0", port=8080)


@get("/")
def index(request):
    return "Hello World"


@get("/health")
def health(request):
    return {"status": "ok"}


app.register_routes(__name__)


if __name__ == "__main__":
    workers = int(os.environ.get("WORKERS", 1))
    app.run(processes=workers)
