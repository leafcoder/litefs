# Gunicorn 配置文件

# 基本配置
bind = "0.0.0.0:8000"  # 绑定地址和端口
workers = 4  # 工作进程数
worker_class = "gevent"  # 使用 gevent  worker 以提高并发性能

# 超时设置
timeout = 30  # 工作进程超时时间（秒）
keepalive = 2  # 保持连接时间（秒）

# 日志配置
accesslog = "./logs/gunicorn_access.log"  # 访问日志文件
errorlog = "./logs/gunicorn_error.log"  # 错误日志文件
loglevel = "info"  # 日志级别

# 进程名称
proc_name = "litefs-app"  # 进程名称

# 服务器钩子
def on_starting(server):
    """服务器启动时执行"""
    import os
    os.makedirs("./logs", exist_ok=True)
    print("Gunicorn server starting...")

def on_exit(server):
    """服务器退出时执行"""
    print("Gunicorn server exiting...")

# 性能优化
backlog = 2048  # 最大挂起连接数
tcp_nodelay = True  # 启用 TCP_NODELAY

# 安全设置
limit_request_line = 4094  # 请求行最大长度
limit_request_fields = 100  # 请求头字段最大数量
limit_request_field_size = 8190  # 请求头字段最大大小