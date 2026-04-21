"""Hello World 应用 - 原生 Asyncio HTTP 服务器"""

import sys
import os
import logging

# 禁用所有日志输出
logging.disable(logging.CRITICAL)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get
from litefs.server.asyncio import run_asyncio

app = Litefs(host="0.0.0.0", port=8080)


@get("/")
async def index(request):
    return "Hello World"


@get("/health")
async def health(request):
    return {"status": "ok"}


app.register_routes(__name__)


if __name__ == "__main__":
    workers = int(os.environ.get("WORKERS", 1))
    run_asyncio(app, host="0.0.0.0", port=8080, processes=workers)
