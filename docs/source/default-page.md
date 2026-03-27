# 默认页面配置

Litefs 支持配置多个默认页面，当访问目录路径时，会按优先级顺序查找默认页面。

## 默认配置

默认情况下，Litefs 会按以下优先级查找默认页面：

1. `index.py` - 动态 Python 文件
2. `index.html` - 静态 HTML 文件

## 配置方法

### 1. 通过代码配置

```python
from litefs import Litefs

# 单个默认页面
app = Litefs(default_page="index")

# 多个默认页面（按优先级顺序）
app = Litefs(default_page="index,index.html,default.html")

app.run()
```

### 2. 通过配置文件

#### YAML 配置

```yaml
# litefs.yaml
default_page: index,index.html,default.html
```

#### JSON 配置

```json
{
  "default_page": "index,index.html,default.html"
}
```

#### TOML 配置

```toml
[files]
default_page = "index,index.html,default.html"
```

### 3. 通过环境变量

```bash
export LITEFS_DEFAULT_PAGE="index,index.html,default.html"
```

## 查找优先级

当访问目录路径（如 `/` 或 `/about/`）时，Litefs 会按以下规则查找默认页面：

1. **解析配置** - 将 `default_page` 配置按逗号分割成列表
2. **遍历查找** - 按顺序查找每个默认页面：
   - 首先查找 `{page_name}.py` 文件（动态文件）
   - 然后查找 `{page_name}` 文件（静态文件）
3. **返回结果** - 找到第一个存在的文件就使用它
4. **回退机制** - 如果所有默认页面都不存在，使用第一个默认页面名称

## 示例

### 示例 1: 基本使用

```python
from litefs import Litefs

app = Litefs(
    webroot="./site",
    default_page="index,index.html"
)

# 访问 http://localhost:9090/
# 会依次查找：
# 1. ./site/index.py
# 2. ./site/index.html
# 3. 使用 index（如果都不存在）
```

### 示例 2: 多个默认页面

```python
from litefs import Litefs

app = Litefs(
    webroot="./site",
    default_page="index,index.html,default.html,home.html"
)

# 访问 http://localhost:9090/
# 会依次查找：
# 1. ./site/index.py
# 2. ./site/index.html
# 3. ./site/default.html
# 4. ./site/home.html
# 5. 使用 index（如果都不存在）
```

### 示例 3: 子目录

```python
from litefs import Litefs

app = Litefs(
    webroot="./site",
    default_page="index,index.html"
)

# 访问 http://localhost:9090/about/
# 会依次查找：
# 1. ./site/about/index.py
# 2. ./site/about/index.html
# 3. 使用 index（如果都不存在）
```

## 动态文件 vs 静态文件

### 动态文件（.py）

动态 Python 文件会被作为 CGI 脚本执行，需要定义 `handler` 函数：

```python
# site/index.py
def handler(self):
    self.start_response(200, [('Content-Type', 'text/html')])
    return ['<html><body>Hello from Python!</body></html>']
```

### 静态文件

静态文件会直接返回内容：

```html
<!-- site/index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>首页</title>
</head>
<body>
    <h1>Hello from HTML!</h1>
</body>
</html>
```

## 优先级规则

对于每个默认页面名称，查找顺序如下：

1. `{name}.py` - 动态 Python 文件（优先）
2. `{name}` - 静态文件（其次）

例如，配置 `default_page="index,index.html"`：

1. 查找 `index.py`
2. 查找 `index.html`
3. 查找 `index.html.py`
4. 查找 `index.html.html`
5. 使用 `index`（如果都不存在）

## 最佳实践

### 1. 开发环境

```python
# 开发环境：优先使用动态文件
app = Litefs(
    webroot="./site",
    default_page="index,index.html",
    debug=True
)
```

### 2. 生产环境

```python
# 生产环境：优先使用静态文件
app = Litefs(
    webroot="./site",
    default_page="index.html,index",
    debug=False
)
```

### 3. 混合环境

```python
# 混合环境：同时支持动态和静态
app = Litefs(
    webroot="./site",
    default_page="index,index.html,default.html,home.html"
)
```

## 注意事项

1. **性能考虑** - 动态文件（.py）需要每次执行，静态文件可以直接返回
2. **缓存机制** - 动态文件会被缓存到内存中，修改后需要重启服务器
3. **安全考虑** - 确保动态文件不包含恶意代码
4. **路径处理** - 默认页面查找会自动处理路径规范化
5. **回退机制** - 如果所有默认页面都不存在，会使用第一个默认页面名称

## 相关配置

- `webroot` - Web 根目录路径
- `not_found` - 404 页面文件名
- `debug` - 调试模式（影响错误处理）

## 相关文档

- [配置管理](config-management.md)
- [API 文档](api.md)
- [项目结构](PROJECT_STRUCTURE.md)
