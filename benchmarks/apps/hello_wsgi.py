"""Hello World 应用 - WSGI 模式"""

import sys
import os

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

# WSGI 应用入口
application = app.wsgi()


if __name__ == "__main__":
    workers = int(os.environ.get("WORKERS", 1))
    app.run(processes=workers)
