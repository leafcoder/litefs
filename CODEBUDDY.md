# CODEBUDDY.md

This file provides guidance to CodeBuddy Code when working with code in this repository.

## Project Overview

Litefs is a lightweight Python web framework providing a high-performance HTTP server with WSGI/ASGI support, built on greenlet/epoll and asyncio. It targets Python 3.8+.

## Build & Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt   # dev tools (pytest, black, ruff, mypy, isort)

# Install the package in editable mode
pip install -e .

# Run all unit tests
pytest tests/unit/ -v

# Run a single test file
pytest tests/unit/test_routing.py -v

# Run a single test function
pytest tests/unit/test_routing.py::test_route_match -v

# Run tests with coverage
pytest tests/unit/ -v --cov=litefs --cov-report=html

# Run only unit/integration/slow tests (markers defined in pyproject.toml)
pytest -m unit
pytest -m integration
pytest -m "not slow"

# Lint and format
black src/litefs tests --line-length 100
isort src/litefs tests --profile black --line-length 100
ruff check src/litefs tests
mypy src/litefs

# Build package
python -m build

# Run benchmarks
cd benchmarks && make benchmark

# Documentation
make docs-serve    # local docs server
make docs-build    # build Sphinx API docs
```

## Architecture

Source code lives under `src/litefs/`. The package is installed from the `src/` layout (`package-dir = {"" = "src"}` in pyproject.toml).

### Core Entry Point: `Litefs` class (`src/litefs/core.py`)

The `Litefs` class is the central application object. It wires together:
- **Router** - URL routing with decorator and method-chain styles
- **CacheManager** - multi-backend caching (Memory, Tree, Redis, Database, Memcache)
- **SessionManager** - session management (Memory, Redis, Database, Memcache backends)
- **MiddlewareManager** - request/response middleware pipeline
- **DatabaseManager** - SQLAlchemy-based database access
- **PluginManager/PluginLoader** - plugin discovery and loading

### Server Implementations (`src/litefs/server/`)

Three server modes, each with its own module:
- `greenlet.py` - Primary server using epoll + greenlet for concurrency. Exports `HTTPServer`, `ProcessHTTPServer`, `WSGIServer`, `mainloop`. This is the default and highest-performance mode.
- `asyncio.py` - Asyncio-based server using `asyncio.start_server`. For async-native workloads.
- `asgi.py` - ASGI-compatible server for integration with Uvicorn/Gunicorn.

### Request Handlers (`src/litefs/handlers/`)

Protocol-specific request processing:
- `socket.py` - `RequestHandler` for the native greenlet server (socket-level HTTP parsing)
- `wsgi.py` - `WSGIRequestHandler` for WSGI deployments
- `asgi.py` - `ASGIRequestHandler` for ASGI deployments
- `response.py` - `Response` class and HTTP status helpers
- `form.py` - Form/multipart parsing for WSGI and ASGI
- `base.py` - `BaseRequestHandler` shared interface

### Routing (`src/litefs/routing/`)

- `router.py` - `Router` class with `add_get/post/put/delete/...` methods and decorator functions (`@get`, `@post`, etc.). Supports path parameters like `/user/{id}`.
- `radix_tree.py` - Radix tree (`RadixTree`, `RadixNode`) for efficient route matching.

### Middleware (`src/litefs/middleware/`)

- `base.py` - `Middleware` base class with sync (`process_request`/`process_response`) and async (`async_process_request`/`async_process_response`) hooks. Async methods take priority in ASGI path.
- Built-in middleware: `cors.py`, `logging.py`, `enhanced_logging.py`, `security.py`, `csrf.py`, `health_check.py`, `rate_limit.py`

### Cache System (`src/litefs/cache/`)

- `cache.py` - `MemoryCache`, `TreeCache` (in-memory backends)
- `redis.py` - Redis cache backend
- `db.py` - Database cache backend
- `memcache.py` - Memcache backend
- `factory.py` - `CacheFactory` and `CacheBackend` enum for creating cache instances
- `manager.py` - `CacheManager` singleton manager
- `form_cache.py` - Form-specific caching

### Session System (`src/litefs/session/`)

Same backend pattern as cache: `session.py` (Memory), `redis.py`, `db.py`, `memcache.py`. Managed via `factory.py` (`SessionBackend` enum) and `manager.py` (`SessionManager`).

### Auth (`src/litefs/auth/`)

- `jwt.py` - JWT token handling
- `oauth2.py` - OAuth2 social login (GitHub, Google, WeChat, Enterprise WeChat)
- `providers.py` - Auth provider definitions
- `decorators.py` - Auth decorators for route handlers
- `middleware.py` - Auth middleware
- `models.py` - Auth data models
- `password.py` - Password utilities

### Other Modules

- `websocket/` - WebSocket server with room management, heartbeat (`server.py`, `connection.py`, `protocol.py`)
- `openapi/` - Auto-generated OpenAPI/Swagger docs (`generator.py`, `ui.py`)
- `database/` - SQLAlchemy wrapper (`core.py`, `models.py`)
- `plugins/` - Plugin system (`base.py`, `loader.py`)
- `debug/` - Debug middleware
- `config.py` - Configuration loading (file, env vars `LITEFS_*`, code kwargs)
- `cli.py` - CLI entry point (`litefs` command)
- `static_handler.py` - Static file serving
- `exceptions.py` - Custom exceptions
- `context.py` - Request context
- `security.py` - Security utilities
- `error_pages.py` - Error page rendering

## Key Patterns

- **Dual-style routing**: Decorator style (`@get('/')`) requires `app.register_routes(__name__)`; method-chain style (`app.add_get('/', handler)`) registers immediately.
- **Factory pattern for backends**: Cache and session backends are selected via enums (`CacheBackend`, `SessionBackend`) and created through factory/manager singletons.
- **Handler return values**: Route handlers can return a string, dict (auto-serialized to JSON), bytes, a 3-tuple `(status, headers, content)`, or an iterable.
- **WSGI/ASGI dual support**: The framework can run standalone (greenlet/asyncio servers) or behind Gunicorn/Uvicorn via `app.wsgi()` / `app.asgi()`.
- **Version**: Defined in `src/litefs/_version.py`, read dynamically by `setup.py` and `pyproject.toml`.

## Test Structure

- `tests/unit/` - Unit tests (pytest)
- `tests/integration/` - Integration tests
- `tests/performance/` - Performance tests
- `tests/stress/` - Stress tests
- `benchmarks/` - Benchmark suite using `wrk`, results in `benchmarks/results/`
