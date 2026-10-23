# Litefs JSON 序列化规范

**文档版本**: 1.0
**最后更新**: 2026-10-22

---

## 概述

Litefs 框架内部**统一使用 [orjson](https://github.com/ijl/orjson)** 做 JSON 序列化，
不再直接依赖标准库 `json`。

选择 orjson 的原因：

| 维度 | 标准库 `json` | orjson |
| --- | --- | --- |
| 实现语言 | 纯 Python（C 加速可选） | Rust |
| 典型序列化吞吐 | 基准 | 约为标准库的 **3~5 倍** |
| 反序列化吞吐 | 基准 | 约为标准库的 **2~4 倍** |
| 非 ASCII 输出 | 默认 `\uXXXX` 转义 | 直接输出原始 UTF-8 |
| 内存占用 | 较高（构建中间对象） | 低（零拷贝路径） |

对 Web 框架而言，JSON 编解码位于**请求热路径**上（请求体解析、响应体序列化、
WebSocket 帧编解码、JWT 签发与校验），吞吐提升直接转化为 P99 延迟收益。

## 唯一出口：`litefs._json`

框架内所有 JSON 读写必须经由 `src/litefs/_json.py` 提供的抽象层，
**业务代码与扩展代码不得直接 `import json` 或 `import orjson`**。

```python
from litefs._json import dumps, dumps_str, dumps_ascii, loads
```

### API 一览

| 函数 | 输入 | 输出 | 用途 |
| --- | --- | --- | --- |
| `dumps(obj, default=None)` | 任意对象 | `bytes`（UTF-8） | 网络响应、WebSocket 帧、加密前字节流 |
| `dumps_str(obj, default=None)` | 任意对象 | `str` | 必须保持字符串类型的调用点 |
| `dumps_ascii(obj, default=None)` | 任意对象 | `str`（纯 ASCII） | 写入要求 ASCII 编码的通道（Memcache） |
| `loads(data)` | `str` / `bytes` / `bytearray` / `memoryview` | 任意对象 | 反序列化 |
| `dump(obj, fp, default=None)` | 任意对象 | 写入二进制文件 | 文件持久化 |
| `load(fp)` | 二进制文件 | 任意对象 | 文件读取 |

### 异常类型

抽象层直接复用 orjson 的异常类，**捕获链与标准库完全兼容**：

- `JSONDecodeError` —— 继承自标准库 `json.JSONDecodeError`（即 `ValueError` 子类）；
- `JSONEncodeError` —— 继承自 `TypeError`。

因此既有代码中的 `except (TypeError, ValueError)`、`except json.JSONDecodeError`
无需修改即可继续工作。

## 语义对齐策略

orjson 与标准库在若干细节上行为不同，抽象层通过序列化选项逐项对齐：

| 场景 | 选项 | 对齐效果 |
| --- | --- | --- |
| 非字符串字典键 | `OPT_NON_STR_KEYS` | `int` / `float` / `bool` / `None` 键转字符串，与标准库一致 |
| `datetime` 对象 | `OPT_PASSTHROUGH_DATETIME` | 交由 `default` 回调处理，`default=str` 输出 `"2026-10-22 12:30:00"` |
| `dataclass` 对象 | `OPT_PASSTHROUGH_DATACLASS` | 交由 `default` 回调处理，`default=str` 输出 `"Point(x=1, y=2)"` |

> **为什么 datetime / dataclass 必须 PASSTHROUGH**
> orjson 原生会把 `datetime` 序列化为 ISO 8601（`"2026-10-22T12:30:00"`）、
> 把 `dataclass` 序列化为对象字典，这与标准库 `json.dumps(..., default=str)`
> 的输出**不同**。启用 PASSTHROUGH 后交由 `default` 回调处理，
> 才能与迁移前逐字节一致。

## 与标准库的固有差异

以下差异为 orjson 的固有行为，**无法通过选项关闭**，使用时需注意：

| 差异点 | 标准库 | orjson | 影响面 |
| --- | --- | --- | --- |
| `NaN` / `Infinity` | 序列化为 `NaN` / `Infinity` 字面量 | 序列化为 `null`；`loads("NaN")` 抛 `JSONDecodeError` | 上游若可能产出非有限浮点，行为改变 |
| 超过 64 位范围的整数 | 任意精度 | 抛出 `TypeError` | 极少数超大整数 ID |
| `UUID` 对象 | 标准模式下抛 `TypeError` | 原生序列化为字符串 | 更宽松，属能力增强 |
| 分隔符 | `", "` / `": "` | `","` / `":"` | 响应体字节数减少；**断言字面量的测试需改为语义断言** |

### 测试断言规范

由于分隔符差异，**测试禁止断言 JSON 字面量**，必须断言 JSON 语义：

```python
# ❌ 错误：绑定到具体序列化器的分隔符风格
assert response.content == '{"path": "/a", "status_code": 200}'

# ✅ 正确：断言语义
import json
assert json.loads(response.content) == {"path": "/a", "status_code": 200}
```

## ASCII 安全出口：`dumps_ascii`

标准库 `json.dumps` 默认 `ensure_ascii=True`，输出纯 ASCII；而 orjson **始终输出原始 UTF-8**。

`pymemcache` 的 `Client.encoding` 默认值为 `"ascii"`，写入时执行
`str(data).encode("ascii")`，非 ASCII 内容会直接抛出
`MemcacheIllegalInputError: Data values must be binary-safe`。

因此，**写入 Memcache 的值必须使用 `dumps_ascii`**：

```python
from litefs._json import dumps_ascii

dumps_ascii({"chinese": "中文", "emoji": "😀"})
# '{"chinese":"\\u4e2d\\u6587","emoji":"\\ud83d\\ude00"}'
```

该出口与标准库 `json.dumps(..., ensure_ascii=True)` **逐字节一致**，
因此：

- 迁移前写入的旧缓存数据可被新代码正确读取（双向兼容）；
- 缓存值的体积与迁移前相同，不会因编码方式变化而膨胀或失效。

框架内使用 `dumps_ascii` 的位置：

- `src/litefs/cache/memcache.py` —— `put()` / `set_many()`
- `src/litefs/session/memcache.py` —— `put()`

其余后端（Redis / Database / Memory / Tree）使用 UTF-8 存储，使用 `dumps_str` 即可。

## 编码规范

### 框架源码

- ✅ 只允许 `from .._json import dumps, dumps_str, dumps_ascii, loads`
- ❌ 禁止 `import json`
- ❌ 禁止 `import orjson`（绕过抽象层会丢失选项配置，导致行为分叉）

### 用户代码

用户应用**不受此约束**，仍可自由使用标准库 `json` 或直接使用 `orjson`。
框架不修改用户进程的全局序列化行为，仅约束框架自身实现。

## 迁移检查清单

引入 orjson 时必须逐项确认：

- [ ] 源码中已无 `import json` 残留（`grep -rn "import json" src/`）
- [ ] `pyproject.toml` / `requirements.txt` 已声明 `orjson>=3.10`
- [ ] 依赖版本兼容目标 Python 基线（orjson 3.10.15 是支持 Python 3.8 的最高版本）
- [ ] 断言 JSON 字面量的测试已改为语义断言
- [ ] 写入 Memcache 的值改用 `dumps_ascii`
- [ ] `Response.content` 等公开属性保持 `str` 类型
- [ ] `make lint`（flake8 + ruff + mypy）通过
- [ ] 全量 `pytest` 通过

## 相关文档

- :doc:`dependency-audit` —— 依赖安全审计（`orjson` 纳入 `requirements.txt` 审计面）
- :doc:`static-checks` —— 静态检查规范
- :doc:`release-roadmap` —— 版本演进路线
