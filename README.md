<div align="center">

# Litefs

<p>
    <!-- Place this tag where you want the button to render. -->
    <a class="github-button" href="https://github.com/leafcoder/litefs/subscription" data-color-scheme="no-preference: light; light: light; dark: dark;" data-show-count="true" aria-label="Watch leafcoder/litefs on GitHub">
        <img alt="GitHub forks" src="https://img.shields.io/github/watchers/leafcoder/litefs?style=social">
    </a>
    <a class="github-button" href="https://github.com/leafcoder/litefs" data-color-scheme="no-preference: light; light: light; dark: dark;" data-show-count="true" aria-label="Star leafcoder/litefs on GitHub">
        <img alt="GitHub forks" src="https://img.shields.io/github/stars/leafcoder/litefs?style=social">
    </a>
    <a class="github-button" href="https://github.com/leafcoder/litefs/fork" data-color-scheme="no-preference: light; light: light; dark: dark;" data-show-count="true" aria-label="Fork leafcoder/litefs on GitHub">
        <img alt="GitHub forks" src="https://img.shields.io/github/forks/leafcoder/litefs?style=social">
    </a>
</p>

<p>
    <img src="https://img.shields.io/github/v/release/leafcoder/litefs" data-origin="https://img.shields.io/github/v/release/leafcoder/litefs" alt="GitHub release (latest by date)">
    <img src="https://img.shields.io/github/languages/top/leafcoder/litefs" data-origin="https://img.shields.io/github/languages/top/leafcoder/litefs" alt="GitHub top language">
    <img src="https://img.shields.io/github/languages/code-size/leafcoder/litefs" data-origin="https://img.shields.io/github/languages/code-size/leafcoder/litefs" alt="GitHub code size in bytes">
    <img src="https://img.shields.io/github/commit-activity/w/leafcoder/litefs" data-origin="https://img.shields.io/github/commit-activity/w/leafcoder/litefs" alt="GitHub commit activity">
    <img src="https://img.shields.io/pypi/dm/litefs" data-origin="https://img.shields.io/pypi/dm/litefs" alt="PyPI - Downloads">
</p>

</div>

Litefs is a lite python web framework.

Build a web server framework using Python. Litefs was developed to implement
a server framework that can quickly, securely, and flexibly build Web
projects. Litefs is a high-performance HTTP server. Litefs has the
characteristics of high stability, rich functions, and low system
consumption.

## Features

- High-performance HTTP server with epoll and greenlet
- WSGI 1.0 compliant (PEP 3333)
- Support for Gunicorn, uWSGI, Waitress, and other WSGI servers
- Static file serving with gzip/deflate compression
- Mako template engine support
- CGI script execution (.pl, .py, .php)
- Session management
- Multi-level caching system (Memory + Tree cache + Redis)
- File monitoring and hot reload
- Python 2.6-3.14 support
- Enhanced request handling with separated query and post parameters
- Comprehensive form validation system
- Beautiful error pages with customization support
- Flexible cache backend selection (Memory, Tree, Redis)

## Quick Start

### Installation

```bash
pip install litefs
```

Or install from source:

```bash
git clone https://github.com/leafcoder/litefs.git
cd litefs
pip install -r requirements.txt
python setup.py install
```

### Basic Usage

#### CLI Tools

Litefs provides powerful CLI tools for quick project creation and development.

**Create a new project:**

```bash
litefs startproject myapp
cd myapp
```

**Start development server:**

```bash
litefs runserver
```

**Show version:**

```bash
litefs version
```

For detailed CLI usage, see [CLI Tools Documentation](docs/build/html/cli-tools.html).

#### Standalone Server

```python
import litefs
litefs.test_server()
```

Or from command line:

```bash
litefs --host localhost --port 9090 --webroot ./site
```

#### WSGI Deployment

Litefs now supports WSGI deployment with Gunicorn, uWSGI, and other
WSGI servers.

Create `wsgi_example.py`:

```python
import litefs
app = litefs.Litefs(webroot='./site')
application = app.wsgi()
```

Deploy with Gunicorn:

```bash
gunicorn -w 4 -b :8000 wsgi_example:application
```

Deploy with uWSGI:

```bash
uwsgi --http :8000 --wsgi-file wsgi_example.py
```

Deploy with Waitress (Windows):

```bash
waitress-serve --port=8000 wsgi_example:application
```

For detailed deployment instructions, see [WSGI_DEPLOYMENT.md](WSGI_DEPLOYMENT.md).

## New Features

### Version Management

Litefs now uses centralized version management with version control tools. Version information is stored in `src/litefs/_version.py` and can be automatically managed through Git tags and build tools.

### Enhanced Request Handling

Litefs provides enhanced request handling with separated query and post parameters:

```python
import litefs

app = litefs.Litefs(webroot='./site')

def handler(request):
    # Access query parameters
    query = request.query
    page = query.get('page', 1)
    
    # Access post parameters
    post = request.post
    username = post.get('username')
    
    return {"page": page, "username": username}
```

### Form Validation

Litefs includes a comprehensive form validation system with multiple validators:

```python
from litefs import (
    required, string_type, number_type, email, url, choice, regex,
    EnhancedRequestHandler, ValidationError
)

def handler(request):
    enhanced = EnhancedRequestHandler(request)
    
    # Validate query parameters
    query_rules = {
        "page": [number_type(min_value=1, max_value=100)],
        "sort": [choice(["asc", "desc"])],
    }
    
    # Validate post parameters
    post_rules = {
        "username": [required(), string_type(min_length=3, max_length=20)],
        "email": [required(), email()],
        "age": [number_type(min_value=0, max_value=120)],
    }
    
    is_valid, errors = enhanced.validate_all(query_rules, post_rules)
    
    if not is_valid:
        return {"errors": errors}
    
    return {"success": True}
```

### Cache Backend Selection

Litefs supports multiple cache backends that can be configured:

```python
import litefs

# Memory cache (default)
app = litefs.Litefs(
    webroot='./site',
    cache_backend='memory',
    cache_max_size=10000
)

# Tree cache
app = litefs.Litefs(
    webroot='./site',
    cache_backend='tree',
    cache_expiration_time=3600,
    cache_clean_period=60
)

# Redis cache
app = litefs.Litefs(
    webroot='./site',
    cache_backend='redis',
    redis_host='localhost',
    redis_port=6379,
    redis_db=0,
    redis_key_prefix='litefs:',
    cache_expiration_time=3600
)
```

### Custom Error Pages

Litefs provides beautiful default error pages and supports custom error pages:

```python
import litefs

# Use default error pages
app = litefs.Litefs(webroot='./site')

# Use custom error pages
app = litefs.Litefs(
    webroot='./site',
    error_pages_dir='./error_pages'
)
```

Create custom error pages in `./error_pages/` directory:
- `400.html` - Bad Request
- `403.html` - Forbidden
- `404.html` - Not Found
- `500.html` - Internal Server Error
- `502.html` - Bad Gateway
- `503.html` - Service Unavailable
- `504.html` - Gateway Timeout

## Project Structure

```
litefs/
├── litefs.py              # Core module
├── setup.py              # Installation configuration
├── requirements.txt       # Dependencies
├── wsgi_example.py       # WSGI example
├── demo/                 # Example code
│   ├── site/            # Example website
│   └── example.py       # Example startup script
├── test/                # Test code
└── docs/                # Documentation
```

## Documentation

Complete documentation is available at [docs/](docs/):

- [在线文档](https://leafcoder.github.io/litefs/) - Online documentation (Sphinx)
- [CLI 工具](docs/build/html/cli-tools.html) - Command line tools guide
- [API 文档](docs/build/html/api.html) - Complete API reference
- [配置管理](docs/build/html/config-management.html) - Configuration management guide
- [健康检查](docs/build/html/health-check.html) - Health check features
- [中间件指南](docs/build/html/middleware-guide.html) - Middleware development guide
- [WSGI 部署](docs/build/html/wsgi-deployment.html) - WSGI deployment guide
- [WSGI 实现](docs/build/html/wsgi-implementation.html) - WSGI implementation details
- [单元测试](docs/build/html/unit-tests.html) - Unit testing documentation
- [性能和压力测试](docs/build/html/performance-stress-tests.html) - Performance and stress testing
- [改进分析](docs/build/html/improvement-analysis.html) - Project improvement analysis
- [测试指南](tests/README.md) - Testing guide
- [Linux 服务器指南](docs/build/html/linux-server-guide.html) - Linux deployment guide
- [开发指南](docs/build/html/development.html) - Development guide
- [项目结构](docs/build/html/project-structure.html) - Project structure
- [待办事项](docs/build/html/todo.html) - Planned features
- [Bug 修复](docs/build/html/bug-fixes.html) - Bug fixes record

### 构建文档

使用 Sphinx 构建文档：

```bash
make docs-build
```

查看文档：

```bash
make docs-serve
```

访问 http://localhost:8000 查看文档。

## License

MIT License - see [LICENSE](LICENSE) for details.

