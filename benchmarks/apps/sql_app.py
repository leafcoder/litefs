"""SQL 查询应用 - 测试数据库操作性能"""

import sys
import os
import logging


# 禁用所有日志输出
logging.disable(logging.CRITICAL)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from litefs import Litefs
from litefs.routing import get
from litefs.orm import Model, Field, SQLiteDB

app = Litefs(host="0.0.0.0", port=8080)

# 使用绝对路径的数据库
DB_PATH = os.path.join(os.path.dirname(__file__), "benchmark.db")
db = SQLiteDB(DB_PATH)


class User(Model):
    table_name = "users"
    id = Field(int, primary_key=True)
    name = Field(str)
    email = Field(str)
    created_at = Field(str)

    class Meta:
        db = db


@get("/init")
def init_db(request):
    """初始化数据库"""
    db.create_tables([User])
    if User.count() == 0:
        for i in range(1000):
            User.create(
                name=f"User{i}",
                email=f"user{i}@test.com",
                created_at="2024-01-01 00:00:00"
            )
    return {"status": "ok", "count": User.count()}


@get("/query")
def query_users(request):
    """简单查询 - 返回 10 条记录"""
    users = User.select().limit(10)
    return {
        "count": len(users),
        "users": [{"id": u.id, "name": u.name, "email": u.email} for u in users]
    }


@get("/query/<int:user_id>")
def get_user(request, user_id: int):
    """单条查询"""
    user = User.get(user_id)
    if user:
        return {"id": user.id, "name": user.name, "email": user.email}
    return {"error": "User not found"}, 404


@get("/health")
def health(request):
    return {"status": "ok"}


app.register_routes(__name__)

# WSGI 应用入口
application = app.wsgi()


if __name__ == "__main__":
    workers = int(os.environ.get("WORKERS", 1))
    app.run(processes=workers)
