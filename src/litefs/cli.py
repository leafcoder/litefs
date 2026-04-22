#!/usr/bin/env python
# coding: utf-8

"""
Litefs CLI 工具

提供项目初始化、开发服务器、数据库管理等命令
"""

import os
import sys
import subprocess
from pathlib import Path
from typing import Optional, List
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


def startproject(project_name: str, directory: Optional[str] = None, template: str = 'basic'):
    """
    创建一个新的 Litefs 项目
    
    Args:
        project_name: 项目名称
        directory: 目标目录（可选，默认为当前目录）
        template: 项目模板（basic, api, fullstack）
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
    print(f"项目模板: {template}")
    
    _create_project_structure(project_path, project_name, template)
    _create_project_files(project_path, project_name, template)
    
    print(f"\n项目 '{project_name}' 创建成功!")
    print(f"\n进入项目目录:")
    print(f"  cd {project_name}")
    print(f"\n安装依赖:")
    print(f"  pip install -r requirements.txt")
    print(f"\n启动开发服务器:")
    print(f"  litefs runserver")
    print(f"\n或者直接运行:")
    print(f"  python app.py")


def _create_project_structure(project_path: Path, project_name: str, template: str):
    """
    创建项目目录结构
    
    Args:
        project_path: 项目根目录
        project_name: 项目名称
        template: 项目模板
    """
    # 基础目录结构
    directories = [
        project_path,
        project_path / "templates",
        project_path / "static",
        project_path / "static" / "css",
        project_path / "static" / "js",
        project_path / "static" / "images",
    ]
    
    # 根据模板添加额外目录
    if template == 'api':
        directories.extend([
            project_path / "models",
            project_path / "routes",
            project_path / "services",
        ])
    elif template == 'fullstack':
        directories.extend([
            project_path / "models",
            project_path / "routes",
            project_path / "services",
            project_path / "migrations",
        ])
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
        print(f"  创建目录: {directory.relative_to(project_path.parent)}")


def _create_project_files(project_path: Path, project_name: str, template: str):
    """
    创建项目文件
    
    Args:
        project_path: 项目根目录
        project_name: 项目名称
        template: 项目模板
    """
    # 文件路径到模板文件的映射
    template_files = {
        "app.py": "app.py.j2",
        "config.yaml": "config.yaml.j2",
        "requirements.txt": "requirements.txt.j2",
        ".gitignore": ".gitignore.j2",
        "README.md": "README.md.j2",
        "wsgi.py": "wsgi.py.j2",
        "templates/index.html": "templates/index.html.j2",
        "templates/about.html": "templates/about.html.j2",
        "static/css/style.css": "site/static/css/style.css.j2",
    }
    
    for file_path, template_name in template_files.items():
        full_path = project_path / file_path
        
        # 获取模板并渲染
        try:
            template = _template_lookup.get_template(template_name)
            content = template.render(project_name=project_name, template=template)
            
            # 如果返回的是 bytes，解码为字符串
            if isinstance(content, bytes):
                content = content.decode('utf-8')
            
            # 写入文件
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  创建文件: {file_path}")
        except Exception as e:
            print(f"  警告: 无法创建文件 {file_path}: {e}")


def runserver(
    host: str = '0.0.0.0',
    port: int = 8080,
    config: str = None,
    debug: bool = False,
    reload: bool = False,
    workers: int = 1,
    **kwargs
):
    """
    运行开发服务器
    
    Args:
        host: 服务器地址
        port: 服务器端口
        config: 配置文件路径
        debug: 调试模式
        reload: 自动重载
        workers: 工作进程数
        **kwargs: 其他配置参数
    """
    if config:
        kwargs["config_file"] = config
    
    try:
        from litefs.core import Litefs
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
    
    print(f"启动 Litefs 开发服务器")
    print(f"地址: http://{host}:{port}")
    print(f"调试模式: {'开启' if debug else '关闭'}")
    print(f"自动重载: {'开启' if reload else '关闭'}")
    print(f"工作进程: {workers}")
    print(f"\n按 Ctrl+C 停止服务器")
    
    app_config = load_config(
        config_file=config,
        host=host,
        port=port,
        debug=debug,
        **kwargs
    )
    
    litefs = (
        Litefs(**app_config.to_dict())
        .add_middleware(LoggingMiddleware)
        .add_middleware(SecurityMiddleware)
        .add_middleware(CORSMiddleware)
        .add_middleware(HealthCheck)
    )
    
    litefs.run()


def shell():
    """
    启动交互式 Shell
    
    提供一个交互式 Python Shell，自动导入 Litefs 和项目模块
    """
    print("Litefs 交互式 Shell")
    print("提示: app, db, models, session 等对象已自动导入")
    print("输入 'exit()' 或按 Ctrl+D 退出\n")
    
    try:
        from litefs.core import Litefs
        import code
        import importlib
        
        # 尝试导入项目模块
        context = {
            'Litefs': Litefs,
            'app': None,
            'db': None,
            'models': None,
            'session': None,
        }
        
        # 尝试导入 app
        try:
            if os.path.exists('app.py'):
                import app as app_module
                context['app'] = getattr(app_module, 'app', None)
                context['db'] = getattr(app_module, 'db', None)
        except ImportError:
            pass
        
        # 尝试导入 models
        try:
            if os.path.exists('models.py'):
                import models
                context['models'] = models
        except ImportError:
            pass
        
        # 启动交互式 Shell
        code.interact(local=context)
        
    except ImportError as e:
        print(f"错误: 无法导入 litefs 模块: {e}")
        print("请确保已安装 litefs: pip install litefs")
        sys.exit(1)


def test(test_path: str = 'tests', verbose: bool = False, coverage: bool = False):
    """
    运行测试
    
    Args:
        test_path: 测试文件或目录路径
        verbose: 详细输出
        coverage: 生成覆盖率报告
    """
    print(f"运行测试: {test_path}")
    
    cmd = ['python', '-m', 'pytest', test_path]
    
    if verbose:
        cmd.append('-v')
    
    if coverage:
        cmd.extend(['--cov=.', '--cov-report=html', '--cov-report=term'])
    
    try:
        subprocess.run(cmd, check=True)
        print("\n测试完成!")
    except subprocess.CalledProcessError as e:
        print(f"\n测试失败: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print("错误: 未找到 pytest")
        print("请安装: pip install pytest pytest-cov")
        sys.exit(1)


def db_init():
    """
    初始化数据库
    
    创建数据库表和初始数据
    """
    print("初始化数据库...")
    
    try:
        # 尝试导入项目的 app 和 models
        if os.path.exists('app.py'):
            import importlib.util
            spec = importlib.util.spec_from_file_location("app", "app.py")
            app_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app_module)
            
            app = getattr(app_module, 'app', None)
            
            if app and hasattr(app, 'db'):
                # 创建所有表
                from litefs.database.models import Base
                Base.metadata.create_all(bind=app.db.engine)
                print("数据库表创建成功!")
            else:
                print("警告: 未找到数据库配置")
        else:
            print("错误: 当前目录不是 Litefs 项目")
            print("请在项目根目录运行此命令")
            sys.exit(1)
            
    except Exception as e:
        print(f"错误: 数据库初始化失败: {e}")
        sys.exit(1)


def db_migrate(message: str = "auto migration"):
    """
    生成数据库迁移脚本
    
    Args:
        message: 迁移消息
    """
    print(f"生成数据库迁移: {message}")
    print("提示: 此功能需要安装 Alembic")
    print("请运行: pip install alembic")


def routes():
    """
    显示所有路由
    """
    print("应用路由列表:\n")
    
    try:
        if os.path.exists('app.py'):
            import importlib.util
            spec = importlib.util.spec_from_file_location("app", "app.py")
            app_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(app_module)
            
            app = getattr(app_module, 'app', None)
            
            if app and hasattr(app, 'router'):
                for route in app.router.routes:
                    methods = ', '.join(route.methods) if route.methods else 'GET'
                    print(f"  {methods:10} {route.path:30} {route.name or ''}")
            else:
                print("未找到路由配置")
        else:
            print("错误: 当前目录不是 Litefs 项目")
            print("请在项目根目录运行此命令")
            sys.exit(1)
            
    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)


def version():
    """显示版本信息"""
    try:
        from litefs._version import __version__
    except ImportError:
        __version__ = "0.8.0"
    
    print(f"Litefs {__version__}")
    print("一个轻量级的 Python Web 框架")
    print("")
    print("使用 'litefs --help' 查看帮助信息")


def main():
    """主函数"""
    import argh
    
    parser = argh.ArghParser()
    parser.add_commands([
        startproject,
        runserver,
        shell,
        test,
        db_init,
        db_migrate,
        routes,
        version
    ])
    parser.dispatch()


if __name__ == "__main__":
    main()
