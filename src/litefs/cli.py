#!/usr/bin/env python
# coding: utf-8

import os
import sys
from pathlib import Path
from typing import Optional
from mako.template import Template
from mako.lookup import TemplateLookup

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 获取模板目录路径
_template_dir = Path(__file__).parent / "templates" / "scaffold"

# 模板查找器
_template_lookup = TemplateLookup(
    directories=[str(_template_dir)],
    input_encoding='utf-8',
    output_encoding='utf-8',
)


def startproject(project_name: str, directory: Optional[str] = None):
    """
    创建一个新的 Litefs 项目
    
    Args:
        project_name: 项目名称
        directory: 目标目录（可选，默认为当前目录）
    """
    # 检查模板目录是否存在
    if not _template_dir.exists():
        print(f"错误: 模板目录不存在: {_template_dir}")
        print(f"请确保已正确安装 litefs 包")
        sys.exit(1)
    
    if not project_name.isidentifier():
        print(f"错误: 项目名称 '{project_name}' 不是有效的 Python 标识符")
        print("项目名称只能包含字母、数字和下划线，且不能以数字开头")
        sys.exit(1)
    
    if directory is None:
        directory = os.getcwd()
    
    project_path = Path(directory) / project_name
    
    if project_path.exists():
        print(f"错误: 目录 '{project_path}' 已存在")
        sys.exit(1)
    
    print(f"创建项目: {project_name}")
    print(f"项目路径: {project_path}")
    
    _create_project_structure(project_path, project_name)
    _create_project_files(project_path, project_name)
    
    print(f"\n项目 '{project_name}' 创建成功!")
    print(f"\n进入项目目录:")
    print(f"  cd {project_name}")
    print(f"\n启动开发服务器:")
    print(f"  litefs runserver")
    print(f"\n或者直接运行:")
    print(f"  python app.py")


def _create_project_structure(project_path: Path, project_name: str):
    """
    创建项目目录结构
    
    Args:
        project_path: 项目根目录
        project_name: 项目名称
    """
    directories = [
        project_path,
        project_path / "site",
        project_path / "site" / "static",
        project_path / "site" / "static" / "css",
        project_path / "site" / "static" / "js",
        project_path / "site" / "static" / "images",
        project_path / "templates",
        project_path / "apps",
        project_path / "apps" / "home",
        project_path / "apps" / "utils",
        project_path / "config",
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  创建目录: {directory.relative_to(project_path.parent)}")


def _create_project_files(project_path: Path, project_name: str):
    """
    创建项目文件
    
    Args:
        project_path: 项目根目录
        project_name: 项目名称
    """
    # 文件路径到模板文件的映射
    template_files = {
        "app.py": "app.py.j2",
        "config.yaml": "config.yaml.j2",
        "requirements.txt": "requirements.txt.j2",
        ".gitignore": ".gitignore.j2",
        "README.md": "README.md.j2",
        "config/__init__.py": "config/__init__.py.j2",
        "config/settings.py": "config/settings.py.j2",
        "config/routes.py": "config/routes.py.j2",
        "apps/__init__.py": "apps/__init__.py.j2",
        "apps/home/__init__.py": "apps/home/__init__.py.j2",
        "apps/home/handlers.py": "apps/home/handlers.py.j2",
        "apps/utils/__init__.py": "apps/utils/__init__.py.j2",
        "apps/utils/helpers.py": "apps/utils/helpers.py.j2",
        "templates/index.html": "templates/index.html.j2",
        "site/static/css/style.css": "site/static/css/style.css.j2",
        "site/index.html": "site/index.html.j2",
        "wsgi.py": "wsgi.py.j2",
    }
    
    for file_path, template_name in template_files.items():
        full_path = project_path / file_path
        
        # 获取模板并渲染
        template = _template_lookup.get_template(template_name)
        content = template.render(project_name=project_name)
        
        # 如果返回的是 bytes，解码为字符串
        if isinstance(content, bytes):
            content = content.decode('utf-8')
        
        # 写入文件
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  创建文件: {file_path}")


def runserver(host: str = None, port: int = None, config: str = None, **kwargs):
    """
    运行开发服务器
    
    Args:
        host: 服务器地址
        port: 服务器端口
        config: 配置文件路径
        **kwargs: 其他配置参数
    """
    if config:
        kwargs["config_file"] = config
    
    try:
        from litefs import Litefs
        from litefs.middleware import (
            CORSMiddleware,
            LoggingMiddleware,
            SecurityMiddleware,
            HealthCheck,
        )
        from litefs.config import load_config
    except ImportError:
        print("错误: 无法导入 litefs 模块")
        print("请确保已安装 litefs: pip install litefs")
        sys.exit(1)
    
    app_config = load_config(config_file=config, **kwargs)
    
    litefs = (
        Litefs(**app_config.to_dict())
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
        .add_middleware(HealthCheck)
    )
    
    litefs.run()


def version():
    """显示版本信息"""
    try:
        from litefs._version import __version__
    except ImportError:
        __version__ = "0.4.0"
    
    print(f"Litefs {__version__}")
    print("一个轻量级的 Python Web 框架")
    print("")
    print("使用 'litefs --help' 查看帮助信息")


def main():
    """主函数"""
    import argh
    
    parser = argh.ArghParser()
    parser.add_commands([startproject, runserver, version])
    parser.dispatch()


if __name__ == "__main__":
    main()
