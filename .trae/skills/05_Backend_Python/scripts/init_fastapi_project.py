#!/usr/bin/env python3
"""
FastAPI 项目初始化脚本
快速生成标准化的 FastAPI 项目结构
"""

import argparse
import os
import sys
from pathlib import Path


def create_project_structure(project_path: str, project_name: str) -> None:
    """
    创建 FastAPI 项目目录结构
    
    Args:
        project_path: 项目根目录路径
        project_name: 项目名称
    """
    base_dir = Path(project_path) / project_name
    
    directories = [
        "app/api/v1/endpoints",
        "app/core",
        "app/models",
        "app/schemas",
        "app/services",
        "app/utils",
        "tests/api",
        "tests/unit",
        "scripts",
    ]
    
    for dir_path in directories:
        (base_dir / dir_path).mkdir(parents=True, exist_ok=True)
    
    files = {
        "app/__init__.py": "",
        "app/main.py": generate_main_py(project_name),
        "app/api/__init__.py": "",
        "app/api/v1/__init__.py": "",
        "app/api/v1/router.py": generate_router_py(),
        "app/api/v1/endpoints/__init__.py": "",
        "app/api/v1/endpoints/health.py": generate_health_endpoint(),
        "app/core/__init__.py": "",
        "app/core/config.py": generate_config_py(),
        "app/models/__init__.py": "",
        "app/schemas/__init__.py": "",
        "app/services/__init__.py": "",
        "app/utils/__init__.py": "",
        "tests/__init__.py": "",
        "tests/conftest.py": generate_conftest_py(),
        "requirements.txt": generate_requirements(),
        "pyproject.toml": generate_pyproject(project_name),
        ".env.example": generate_env_example(),
        "README.md": generate_readme(project_name),
    }
    
    for file_path, content in files.items():
        file_full_path = base_dir / file_path
        file_full_path.write_text(content, encoding="utf-8")
    
    print(f"✅ FastAPI 项目 '{project_name}' 已创建于: {base_dir}")


def generate_main_py(project_name: str) -> str:
    return f'''"""
{project_name} - FastAPI 应用入口
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["Root"])
async def root():
    return {{"message": "Welcome to {project_name}", "docs": "/docs"}}
'''


def generate_router_py() -> str:
    return '''"""
API 路由聚合
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health

api_router = APIRouter()

api_router.include_router(health.router, prefix="/health", tags=["Health"])
'''


def generate_health_endpoint() -> str:
    return '''"""
健康检查端点
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
async def health_check():
    """服务健康检查"""
    return {"status": "healthy", "service": "fastapi"}
'''


def generate_config_py() -> str:
    return '''"""
应用配置管理
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Project"
    VERSION: str = "0.1.0"
    API_V1_PREFIX: str = "/api/v1"
    
    ALLOWED_ORIGINS: list[str] = ["*"]
    
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
'''


def generate_conftest_py() -> str:
    return '''"""
Pytest 配置
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)
'''


def generate_requirements() -> str:
    return '''fastapi>=0.109.0
uvicorn[standard]>=0.27.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-dotenv>=1.0.0

# 测试依赖
pytest>=7.4.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
'''


def generate_pyproject(project_name: str) -> str:
    return f'''[project]
name = "{project_name}"
version = "0.1.0"
description = "FastAPI Project"
requires-python = ">=3.10"

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
'''


def generate_env_example() -> str:
    return '''PROJECT_NAME=FastAPI Project
VERSION=0.1.0

DATABASE_URL=postgresql://user:password@localhost:5432/dbname
REDIS_URL=redis://localhost:6379/0
'''


def generate_readme(project_name: str) -> str:
    return f'''# {project_name}

FastAPI 项目模板

## 快速开始

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 项目结构

```
app/
├── api/v1/endpoints/  # API 端点
├── core/              # 核心配置
├── models/            # 数据模型
├── schemas/           # Pydantic 模式
├── services/          # 业务逻辑
└── utils/             # 工具函数

tests/
├── api/               # API 测试
└── unit/              # 单元测试
```

## API 文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
'''


def main():
    parser = argparse.ArgumentParser(description="初始化 FastAPI 项目")
    parser.add_argument("project_name", help="项目名称")
    parser.add_argument("--path", default=".", help="项目创建路径 (默认: 当前目录)")
    
    args = parser.parse_args()
    
    create_project_structure(args.path, args.project_name)


if __name__ == "__main__":
    main()
