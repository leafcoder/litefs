# Litefs 测试指南

## 测试类型

Litefs 项目包含三种类型的测试：

1. **单元测试** - 验证各个模块的功能正确性
2. **性能测试** - 测量系统在正常负载下的性能表现
3. **压力测试** - 验证系统在高并发和极端负载下的稳定性

## 测试目录结构

```
tests/
├── unit/                           # 单元测试
│   ├── test_basic.py
│   ├── test_cache.py
│   ├── test_core.py
│   ├── test_environ.py
│   ├── test_form.py
│   ├── test_health_check.py
│   ├── test_max_request_size.py
│   ├── test_memorycache.py
│   ├── test_middleware.py
│   ├── test_session.py
│   └── test_treecache.py
├── performance/                    # 性能测试
│   └── test_performance.py
├── stress/                         # 压力测试
│   └── test_stress.py
├── run_tests.py                    # 运行所有单元测试
└── run_performance_stress_tests.py # 运行性能和压力测试
```

## 快速开始

### 运行所有单元测试

```bash
python tests/run_tests.py
```

### 运行性能测试和压力测试

```bash
python tests/run_performance_stress_tests.py
```

### 运行特定测试

```bash
# 运行单个测试文件
python tests/unit/test_core.py
python tests/performance/test_performance.py
python tests/stress/test_stress.py

# 运行特定测试类
python -m unittest tests.unit.test_core.TestMakeConfig

# 运行特定测试方法
python -m unittest tests.unit.test_core.TestMakeConfig.test_default_config
```

## 测试覆盖范围

### 单元测试 (132 个测试)

| 模块 | 测试数量 | 状态 |
|------|----------|------|
| 核心功能 | 12 | ✅ 通过 |
| 缓存系统 | 15 | ✅ 通过 |
| 会话管理 | 9 | ✅ 通过 |
| 中间件系统 | 20 | ✅ 通过 |
| 健康检查 | 12 | ✅ 通过 |
| 请求处理 | 15 | ✅ 通过 |
| 表单解析 | 11 | ✅ 通过 |
| 请求大小限制 | 9 | ✅ 通过 |
| 基本功能 | 5 | ✅ 通过 |
| 内存缓存 | 11 | ✅ 通过 |
| 树缓存 | 13 | ✅ 通过 |

### 性能测试 (12 个测试)

| 模块 | 测试数量 | 状态 |
|------|----------|------|
| MemoryCache 性能 | 4 | ✅ 通过 |
| TreeCache 性能 | 3 | ✅ 通过 |
| parse_form 性能 | 3 | ✅ 通过 |
| Session 性能 | 2 | ✅ 通过 |

### 压力测试 (10 个测试)

| 模块 | 测试数量 | 状态 |
|------|----------|------|
| MemoryCache 压力 | 3 | ✅ 通过 |
| TreeCache 压力 | 2 | ✅ 通过 |
| parse_form 压力 | 1 | ✅ 通过 |
| Session 压力 | 2 | ✅ 通过 |
| 内存泄漏测试 | 2 | ✅ 通过 |

## 性能基准

### MemoryCache

| 操作 | 吞吐量 | 延迟 |
|------|--------|------|
| put | > 3,000,000 ops/s | < 0.001ms |
| get | > 5,000,000 ops/s | < 0.0005ms |
| delete | > 6,000,000 ops/s | < 0.001ms |

### TreeCache

| 操作 | 吞吐量 | 延迟 |
|------|--------|------|
| put | > 100,000 ops/s | < 0.01ms |
| get | > 2,000,000 ops/s | < 0.001ms |
| delete | > 2,000 ops/s | < 0.5ms |

### parse_form

| 表单类型 | 吞吐量 | 延迟 |
|---------|--------|------|
| 简单表单 | > 400,000 ops/s | < 0.01ms |
| 复杂表单 | > 100,000 ops/s | < 0.05ms |
| 大表单 | > 10,000 ops/s | < 0.1ms |

### Session

| 操作 | 吞吐量 | 延迟 |
|------|--------|------|
| 创建 | > 3,000,000 sessions/s | < 0.001ms |
| 访问 | > 40,000,000 ops/s | < 0.00005ms |

## 依赖安装

### 基础依赖

```bash
pip install -r requirements.txt
```

### 性能测试依赖

```bash
pip install -r requirements-performance.txt
```

## CI/CD 集成

### GitHub Actions 示例

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      - name: Run unit tests
        run: python tests/run_tests.py

  performance-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-performance.txt
      - name: Run performance and stress tests
        run: python tests/run_performance_stress_tests.py
```

## 注意事项

1. **测试环境**：在类似生产环境的硬件上运行测试
2. **预热**：在正式测试前进行预热，避免冷启动影响
3. **多次运行**：多次运行测试取平均值，减少误差
4. **资源监控**：监控 CPU、内存、磁盘 I/O 等资源使用情况
5. **基准对比**：与历史基准对比，及时发现性能退化

## 故障排查

### 性能下降

1. 检查是否有内存泄漏
2. 检查是否有锁竞争
3. 检查是否有不必要的对象创建
4. 检查是否有低效的算法

### 并发问题

1. 检查是否有死锁
2. 检查是否有竞态条件
3. 检查是否有线程安全问题
4. 检查是否有资源争用

### 内存问题

1. 使用 memory-profiler 分析内存使用
2. 检查是否有循环引用
3. 检查是否有大对象未释放
4. 检查是否有缓存未清理

## 持续改进

建议定期运行测试：
- 每次代码提交后运行单元测试
- 每周运行完整的性能和压力测试
- 在发布前进行全面的测试验证
- 建立性能基准和监控指标
- 及时发现和解决问题

## 测试统计

| 测试类型 | 测试数量 | 状态 |
|---------|----------|------|
| 单元测试 | 132 | ✅ 全部通过 |
| 性能测试 | 12 | ✅ 全部通过 |
| 压力测试 | 10 | ✅ 全部通过 |
| **总计** | **154** | **✅ 全部通过** |

## 文档

- [单元测试文档](docs/auto-generated/unit-tests.md)
- [性能测试和压力测试文档](docs/auto-generated/performance-stress-tests.md)
- [健康检查文档](docs/auto-generated/health-check.md)
