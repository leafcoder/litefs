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
- Multi-level caching system (Memory + Tree cache)
- File monitoring and hot reload
- Python 2.6-3.14 support

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

- [WSGI Deployment Guide](WSGI_DEPLOYMENT.md) - Detailed deployment instructions
- [TODO.md](TODO.md) - Planned features

## License

MIT License - see [LICENSE](LICENSE) for details.

