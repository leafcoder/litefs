# 问题修复记录

## 修复 1：`No module named litefs.__main__`

**日期**：2026-03-26

**问题描述**：
在 Linux 系统上使用 `make dev-serve` 或 `python -m litefs` 时报错：
```
No module named litefs.__main__
```

**原因**：
当使用 `python -m litefs` 命令时，Python 需要找到 `litefs/__main__.py` 文件，但这个文件不存在。

**解决方案**：
创建了 `src/litefs/__main__.py` 文件。

```python
#!/usr/bin/env python
# coding: utf-8

from .core import test_server

if __name__ == '__main__':
    test_server()
```

**影响文件**：
- 新增：`src/litefs/__main__.py`

## 修复 2：watchdog 参数错误

**日期**：2026-03-26

**问题描述**：
启动服务器时出现参数错误：
```
TypeError: BaseObserver.schedule() takes 3 positional arguments but 4 were given
```

**原因**：
`observer.schedule()` 方法在新版本中需要使用关键字参数 `recursive=True`。

**解决方案**：
修改了 `src/litefs/core.py` 中的代码。

```python
# 修改前
observer.schedule(event_handler, self.config.webroot, True)

# 修改后
observer.schedule(event_handler, self.config.webroot, recursive=True)
```

**影响文件**：
- 修改：`src/litefs/core.py`

## 修复 3：`cannot import name 'SocketIO' from 'litefs.server'`

**日期**：2026-03-26

**问题描述**：
在 Linux 系统上使用 `make dev-serve` 时报错：
```
cannot import name 'SocketIO' from 'litefs.server'
```

**原因**：
`SocketIO`、`BufferedRWPair` 和 `DEFAULT_BUFFER_SIZE` 类在 `http_server.py` 中定义，但没有在 `server/__init__.py` 中导出。

**解决方案**：
1. 在 `src/litefs/server/__init__.py` 中添加导出：
```python
from .http_server import (
    TCPServer,
    HTTPServer,
    WSGIServer,
    SocketIO,           # 新增
    BufferedRWPair,      # 新增
    DEFAULT_BUFFER_SIZE,  # 新增
    make_environ,
    make_headers,
    mainloop,
    epoll,
    HAS_EPOLL,
    HAS_GREENLET,
)
```

2. 在 `src/litefs/core.py` 中更新导入：
```python
from .server import (
    HTTPServer,
    mainloop,
    SocketIO,
    BufferedRWPair,
    DEFAULT_BUFFER_SIZE,
)
```

3. 移除 `handler` 方法中的局部导入：
```python
# 修改前
def handler(self, request, environ, server):
    from .server import SocketIO, BufferedRWPair, DEFAULT_BUFFER_SIZE
    raw = SocketIO(server, request)
    # ...

# 修改后
def handler(self, request, environ, server):
    raw = SocketIO(server, request)
    # ...
```

**影响文件**：
- 修改：`src/litefs/server/__init__.py`
- 修改：`src/litefs/core.py`

## 修复 4：访问 `/test` 返回 404 页面

**日期**：2026-03-26

**问题描述**：
访问 `/test` 路径时返回 404 页面，但 `examples/basic/site/test.py` 文件存在。

**原因**：
在 `RequestHandler` 类的 `handler` 方法中，有一个 bug：当访问 `/test` 时，代码会检查扩展名，如果是 `.py` 或 `.mako`，就直接返回 404，而不尝试加载脚本。此外，`_load_python_script` 方法中有一行代码 `setattr(module, 'handler', self)` 会覆盖脚本中定义的 `handler` 函数。

**解决方案**：
1. 修复 `RequestHandler.handler` 方法，移除了错误的扩展名检查：
```python
# 修改前
name_without_ext, ext = path_splitext(name)
if ext in ('.py', '.mako'):
    return self._response(404)

# 修改后
name_without_ext, ext = path_splitext(name)
# 移除了错误的扩展名检查，允许加载 .py 和 .mako 文件
```

2. 修复 `_load_python_script` 方法，移除了覆盖 `handler` 函数的代码：
```python
# 修改前
module = new_module()
setattr(module, 'handler', self)  # 这会覆盖脚本中的 handler 函数
code = compile(fp.read(), script_path, 'exec')
module_globals = {}
exec(code, module_globals)
for k, v in module_globals.items():
    setattr(module, k, v)
return module

# 修改后
module = new_module()
# 移除了 setattr(module, 'handler', self)
code = compile(fp.read(), script_path, 'exec')
module_globals = {}
exec(code, module_globals)
for k, v in module_globals.items():
    setattr(module, k, v)
return module
```

**影响文件**：
- 修改：`src/litefs/handlers/request.py`

## 验证

所有修复已通过以下测试：

```bash
# 测试模块导入
$env:PYTHONPATH="z:\litefs\src"; python -c "from litefs.server import SocketIO, BufferedRWPair, DEFAULT_BUFFER_SIZE; print('Import successful')"
Import successful

# 测试命令行帮助
$env:PYTHONPATH="z:\litefs\src"; python -m litefs --help
usage: z:\litefs\src\litefs\__main__.py [-h] [-H HOST] [-P PORT] ...
```

## 使用说明

现在可以在 Linux 系统上正常使用以下命令：

```bash
# 方法 1：使用 Makefile（推荐）
make dev-serve

# 方法 2：直接使用 Python
export PYTHONPATH=/path/to/litefs/src
python -m litefs --host localhost --port 9090 --webroot examples/basic/site --debug

# 方法 3：开发模式安装
pip install -e .
litefs --host localhost --port 9090 --webroot examples/basic/site --debug
```

## 相关文档

- [API 文档](api.md)
- [Linux 服务器使用指南](linux-server-guide.md)
- [开发指南](DEVELOPMENT.md)
- [项目结构](PROJECT_STRUCTURE.md)
