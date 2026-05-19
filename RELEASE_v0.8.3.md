# LiteFS v0.8.3 Release Notes

## 重大改进

### 简化包导入结构
- 移除 `__init__.py` 中的 `__getattr__` 延迟导入机制和庞大的 `__all__` 列表（203行 → 31行）
- 所有代码改为从子模块直接导入（如 `from litefs.core import Litefs`），降低维护复杂度
- 同步更新所有测试文件（28个）、示例代码（10个）、文档（24个）中的导入方式

### 异步错误处理重构
- 提取 `_build_error_parts` 公共方法，消除 `_handle_error_parts` 与 `_async_handle_error_parts` 的重复代码

### WSGI 输入流修复
- 读取 `wsgi.input` 后重置流位置（`seek(0)`），确保后续中间件可重新读取请求体
- 提取 `_reset_input_stream` 静态方法，3处重复逻辑统一调用，增加 `try/except` 防御

### 限流中间件测试修复
- 修复 `RateLimitMiddleware` 和 `ThrottleMiddleware` 测试用例，适配 `Response` 对象返回类型（原先错误地期望元组）

### 日志系统健壮性
- 修复 `log_info`/`log_error`/`log_debug` 在 `logger=None` 时的 `AttributeError`，回退到 `logging` 模块级 logger
- `DatabaseManager.close_all()` 改用有效 logger 而非传入 `None`

### Benchmark 测试脚本全面优化
- 修复 `fastapi_uvicorn_server.py` 多 worker 启动问题（必须使用 `"module:app"` 字符串引用）
- 修复 `wait_for_server` 计时错误（原实际只等待 ~7.5s 却声称 15s）
- 修复 `median_of` 偶数长度中位数计算错误
- 增加信号处理（Ctrl+C 清理残留进程）、依赖检查、端口冷却等待
- 按进程组去重杀进程，避免重复操作
- LiteFS 服务器添加 `session_secure=True` 消除开发环境警告
- 增加 `logging.disable(logging.CRITICAL)` 禁用日志输出干扰

## Bug 修复

- 修复服务器关闭时 `DatabaseManager.close_all()` 的 `AttributeError: 'NoneType' object has no attribute 'info'`
- 修复 `RateLimitMiddleware` 测试中 `'Response' object is not subscriptable` 错误
- 修复 WSGI 输入流读取后未重置位置导致后续中间件无法读取请求体的问题

## 文件变更统计

- `src/litefs/__init__.py`: 203 → 31 行（-84.7%）
- `src/litefs/core.py`: 提取公共错误处理方法
- `src/litefs/handlers/wsgi.py`: 新增 `_reset_input_stream` 方法
- `src/litefs/utils/utils.py`: 日志函数 None 防御
- `src/litefs/database/core.py`: 修复 close_all 日志调用
- `tests/performance/run_test.sh`: 全面重构优化
- 28 个测试文件、10 个示例、24 个文档文件：更新导入方式
