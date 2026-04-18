"""Hello World 应用 - ASGI 模式"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get

app = Litefs(host="0.0.0.0", port=8080)


@get("/")
async def index(request):
    return "Hello World"


@get("/health")
async def health(request):
    return {"status": "ok"}


app.register_routes(__name__)

# ASGI 应用入口
application = app.asgi()


if __name__ == "__main__":
    workers = int(os.environ.get("WORKERS", 1))
    app.run(processes=workers)
