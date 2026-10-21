# Litefs 依赖安全审计

**文档版本**: 1.0
**最后更新**: 2026-10-21

---

## 概述

框架的运行时依赖一旦出现已知漏洞（CVEs / GHSA），用户安装 Litefs 时会**连带引入风险**。
依赖安全审计的目标是：在发布前自动发现"我们依赖的第三方包存在已知漏洞"，
并把处置结论固化到流水线里。

Litefs 的做法：

- 使用 [pip-audit](https://pypi.org/project/pip-audit/) 作为扫描引擎——它直接查询
  PyPI 官方漏洞数据库（PyPI Advisory Database）并结合 OSV 数据源，覆盖 CVE 与 GHSA。
- 用 `scripts/audit_deps.py` 封装，纯标准库实现，**不向项目引入新依赖**。
- 接入 `make audit` 与 CI 的 `security` job。

## 快速开始

```bash
# 安装 pip-audit
pip install 'pip-audit>=2.7.3'

# 审计运行时依赖（默认审计 requirements.txt）
make audit
```

输出：

```text
No known vulnerabilities found
[PASS] 未发现已知依赖漏洞
```

## 审计面

`scripts/audit_deps.py` 支持两种审计面，由 `--env` 切换：

| 模式 | 审计对象 | 命令 | 适用场景 |
| --- | --- | --- | --- |
| **默认** | `requirements.txt` 列出的运行时依赖 | `pip-audit -r requirements.txt` | 发布前的依赖面体检 |
| `--env` | 当前 Python 环境的全部已安装包 | `pip-audit` | 开发环境自查、排查间接依赖 |

### 为什么默认只审 requirements.txt

**审计面必须收敛到"发布给用户的依赖面"。**

`requirements.txt` 描述的是 Litefs 安装时会被拉进来的包，这是真正传递给用户的攻击面。
而 `--env` 模式会扫描当前环境里的**全部**已安装包，包括 pytest、starlette、urllib3、
pip、setuptools 等测试与构建工具链。这些包的漏洞：

- **不影响用户**——用户不会因为安装了 Litefs 而装上 pytest；
- **数量大、噪声高**——一次全环境扫描可能报出十几条 CVE，全部需要人工甄别；
- **会淹没真实信号**——真正需要修的运行时依赖漏洞被埋在噪声里，最终无人处理。

因此 CI 中的 `security` job 使用默认模式（审 `requirements.txt`）。
`--env` 模式保留为开发期自查工具，需要时手动执行。

## 命令行参数

```text
python scripts/audit_deps.py [选项]

  --format {text,json}   输出格式（默认: text）
  --output PATH          结果落盘路径，未指定时仅输出到标准输出
  --requirement PATH     审计指定的 requirements 文件（默认: requirements.txt）
  --env                  审计当前 Python 环境而非 requirements 文件
  --skip-editable        跳过以可编辑模式安装的包（配合 --env 使用）
  --ignore-vuln ID       忽略指定漏洞编号，可重复传入
```

### 输出格式

**文本模式**——stdout 输出 pip-audit 的原始报告：

```bash
python scripts/audit_deps.py
```

**JSON 模式**——stdout **仅输出 JSON 文档**，摘要与结论行写入 stderr。
这样 CI 可以直接 `json.load` 解析 stdout，同时人仍能在日志里看到结论：

```bash
python scripts/audit_deps.py --format json --output reports/audit.json
```

```json
{
  "dependencies": [
    {
      "name": "jinja2",
      "version": "3.1.4",
      "vulns": [
        {
          "id": "GHSA-h5c8-rqwp-c5g7",
          "aliases": ["CVE-2024-56326"],
          "fix_versions": ["3.1.5"]
        }
      ]
    }
  ]
}
```

> **实现要点**：JSON 纯净性靠 `_emit()` 辅助函数保证——所有 `[PASS]` / `[FAIL]`
> 结论行在 JSON 模式下强制写 stderr。早期实现无条件 `print()` 到 stdout，
> 会导致 `json.load(sys.stdin)` 直接失败。

### 忽略已评估的漏洞

某些漏洞在实际部署场景中不可利用（如仅影响特定可选依赖的特定调用路径），
可以用 `--ignore-vuln` 显式豁免，但**必须同时在代码或文档中记录评估结论**：

```bash
python scripts/audit_deps.py --ignore-vuln GHSA-xxxx-xxxx-xxxx
```

> **红线**：豁免不是"消音器"。每一条 `--ignore-vuln` 都应有对应的评估记录，
> 说明为何不可利用、影响范围是什么、是否有缓解措施。

## 退出码语义

| 退出码 | 含义 | 触发条件 |
| --- | --- | --- |
| `0` | 未发现漏洞 | pip-audit 返回 0 |
| `1` | **发现漏洞** | pip-audit 返回 1 |
| `2` | 工具不可用 | pip-audit 未安装，或执行过程异常 |

pip-audit 未安装时，脚本会给出明确指引而非抛出原始 traceback：

```text
[FAIL] 未安装 pip-audit，请执行 pip install 'pip-audit>=2.7.3' 或 pip install pip-audit
```

## 接入 CI

`.gitlab-ci.yml` 中的 `security` job：

```yaml
security:
  stage: verify
  extends: .python
  script:
    - echo ">>> pip-audit 依赖安全审计"
    - python scripts/audit_deps.py --format json --output reports/audit.json
  allow_failure: true
  artifacts:
    when: always
    expire_in: 1 week
    paths:
      - reports/audit.json
```

设计要点：

- **`allow_failure: true`**——漏洞扫描是**告警**而非**门禁**。发现漏洞后需要人工评估
  影响面并决定是升级依赖还是豁免，直接阻塞流水线会打断正常发布节奏。
- **`artifacts: when: always`**——即使审计失败，JSON 报告也会归档，便于事后追溯。
- **`expire_in: 1 week`**——报告体积小但时效性强，一周足够排查。

## 接入 Makefile

```make
audit:
	@echo ">>> 依赖安全审计（pip-audit）"
	@python scripts/audit_deps.py
	@echo "依赖安全审计完成"
```

`make help` 中的「性能与安全」段落列出了该命令。

## 依赖声明

`pyproject.toml` 的 `dev` 可选依赖组中已声明：

```toml
[project.optional-dependencies]
dev = [
    "pip-audit>=2.7.3",
]
```

执行 `make sync-deps` 后即可使用。

## 漏洞处置流程

1. **CI 报告**：`security` job 在流水线中给出漏洞清单。
2. **影响面评估**：确认漏洞是否位于**运行时依赖面**（即 `requirements.txt` 中的包）。
   仅存在于测试工具链的漏洞不阻塞发布。
3. **处置**：
   - 有修复版本 → 升级 `requirements.txt` 中的版本约束，重新跑全量测试；
   - 无修复版本 → 评估是否可利用；不可利用则用 `--ignore-vuln` 豁免并记录评估结论；
   - 影响核心功能且无修复版本 → 考虑替换该依赖或实现降级方案。
4. **回归验证**：`make lint` + `make test` 确认升级未引入问题。

## 常见问题

**Q：为什么 `pip-audit` 不在 `requirements.txt` 里？**

A：它是**开发期工具**，不是运行时依赖。放在 `[project.optional-dependencies].dev` 中，
通过 `make sync-deps` 安装，不影响用户安装 Litefs。

**Q：能不能直接在 CI 里 `pip install pip-audit`？**

A：可以，但项目统一用 `pyproject.toml` 声明可选依赖，`make sync-deps` 一次装齐，
避免在 CI 脚本里散落临时的 pip install。

**Q：扫描结果里的 `fix_versions: []` 是什么意思？**

A：该漏洞**尚无修复版本**，上游未发布补丁。这类情况需要评估影响面并做豁免，
同时关注上游进展。

**Q：能否只扫某个特定的包？**

A：可以。生成一个只含目标包的临时 requirements 文件，用 `--requirement` 指向它：

```bash
echo "requests==2.32.3" > /tmp/req.txt
python scripts/audit_deps.py --requirement /tmp/req.txt
```

## 相关文档

- :doc:`static-checks` —— 静态检查（flake8 / ruff / mypy）规范
- :doc:`unit-tests` —— 单元测试规范与执行方式
- :doc:`development` —— 开发环境搭建
- :doc:`todolist` —— 项目规划与阶段进度
