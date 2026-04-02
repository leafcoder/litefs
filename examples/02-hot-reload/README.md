# LiteFS 热重载功能

## 功能概述

LiteFS 支持开发环境下的热重载功能，当检测到项目文件发生变化时，会自动重新加载应用，包括：

- **Python 源文件** (`.py`)
- **配置文件** (`.yaml`, `.yml`, `.json`, `.ini`, `.conf`)

## 工作原理

1. **文件监控**：使用 `watchdog` 库监控启动脚本当前目录下的所有文件
2. **智能判断**：区分不同类型的文件变化
   - Python 文件和配置文件变化 → 重新加载整个应用
   - 其他文件变化 → 仅清空缓存
3. **自动重载**：当检测到需要重载的文件时：
   - 关闭当前服务器
   - 清理模块缓存
   - 重新执行主模块
   - 启动新的服务器实例

## 使用方法

### 基本用法

```python
from litefs import Litefs
from litefs.routing import get

app = Litefs(host='0.0.0.0', port=8080, debug=True)

@get('/')
def index_handler(request):
    return "Hello World"

app.register_routes(__name__)

if __name__ == '__main__':
    # 启动服务器，poll_interval 设置得小一些以便快速响应文件变化
    app.run(poll_interval=0.1, processes=1)
```

### 示例

运行热重载示例：

```bash
cd examples/02-hot-reload
python demo_hot_reload.py
```

访问 http://localhost:8080，然后修改 `demo_hot_reload.py` 文件中的 `index_handler` 函数，保存后刷新浏览器即可看到变化。

## 配置参数

### poll_interval

文件监控轮询间隔（秒），默认值为 `0.2`。

```python
app.run(poll_interval=0.1)  # 更频繁地检查文件变化
```

### processes

服务器进程数。热重载功能在单进程模式下工作最佳。

```python
app.run(processes=1)  # 单进程模式（推荐用于开发）
```

## 注意事项

1. **生产环境**：热重载功能主要用于开发环境，生产环境应禁用
2. **多进程模式**：热重载在多进程模式下可能无法正常工作
3. **模块状态**：重新加载时，全局变量和模块级状态会被重置
4. **数据库连接**：重新加载时，确保正确关闭数据库连接
5. **Session 数据**：使用内存 Session 时，重新加载会导致 Session 数据丢失

## 文件变化处理

### Python 文件变化

当 `.py` 文件发生变化时：

1. 清空所有缓存
2. 关闭当前服务器
3. 清理模块缓存
4. 重新执行主模块
5. 启动新的服务器实例

### 配置文件变化

当配置文件（`.yaml`, `.yml`, `.json`, `.ini`, `.conf`）发生变化时：

1. 清空所有缓存
2. 关闭当前服务器
3. 重新加载配置
4. 重新执行主模块
5. 启动新的服务器实例

### 其他文件变化

当其他文件（如模板、静态文件）发生变化时：

1. 仅清空缓存
2. 服务器继续运行
3. 下次请求时会使用新文件

## 故障排除

### 热重载不工作

1. 确保 `debug=True`
2. 检查 `poll_interval` 是否设置得太长
3. 确保文件监控目录正确（启动脚本当前目录）

### 重新加载后状态丢失

这是预期行为。重新加载会重新执行主模块，全局变量会被重置。建议使用：

- 外部存储（如 Redis、数据库）保存状态
- Session 机制保存用户数据

### 文件变化但未重新加载

1. 检查文件扩展名是否在监控列表中
2. 检查文件是否保存在启动脚本当前目录下
3. 查看日志输出，确认文件变化被检测到

## 日志输出

热重载相关的日志输出：

```
[2026/04/02 10:00:00] INFO - File modified: /path/to/file.py, reloading application...
[2026/04/02 10:00:00] INFO - Reloading application from /path/to/app.py
[2026/04/02 10:00:00] INFO - Starting server on 0.0.0.0:8080 (processes=1)
```

## 性能优化

1. **排除不必要的目录**：确保 `__pycache__`、`.git` 等目录不在监控范围内
2. **调整轮询间隔**：根据项目大小调整 `poll_interval`
3. **使用单进程模式**：热重载在单进程模式下效率最高

## 最佳实践

1. **开发环境**：始终启用 `debug=True` 和热重载
2. **生产环境**：禁用热重载，使用预编译和缓存
3. **代码组织**：将业务逻辑放在单独的模块中，便于重新加载
4. **状态管理**：避免在全局变量中保存重要状态
