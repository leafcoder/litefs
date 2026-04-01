#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from litefs import Litefs, Config, load_config
from litefs.routing import get


def example_default_config():
    """示例 1: 使用默认配置"""
    print("=== 示例 1: 使用默认配置 ===")
    
    app = Litefs()
    
    print(f"Host: {app.config.host}")
    print(f"Port: {app.config.port}")
    print(f"Webroot: {app.config.webroot}")
    print(f"Debug: {app.config.debug}")
    print()


def example_code_config():
    """示例 2: 使用代码配置"""
    print("=== 示例 2: 使用代码配置 ===")
    
    app = Litefs(
        host='0.0.0.0',
        port=8080,
        webroot='../01-quickstart/site',
        debug=True,
        max_request_size=20971520,
    )
    
    print(f"Host: {app.config.host}")
    print(f"Port: {app.config.port}")
    print(f"Webroot: {app.config.webroot}")
    print(f"Debug: {app.config.debug}")
    print(f"Max request size: {app.config.max_request_size}")
    print()


def example_yaml_config():
    """示例 3: 使用 YAML 配置文件"""
    print("=== 示例 3: 使用 YAML 配置文件 ===")
    
    config_file = '../common/config/litefs.yaml'
    
    if os.path.exists(config_file):
        app = Litefs(config_file=config_file)
        
        print(f"配置文件: {config_file}")
        print(f"Host: {app.config.host}")
        print(f"Port: {app.config.port}")
        print(f"Webroot: {app.config.webroot}")
        print(f"Debug: {app.config.debug}")
        print()
    else:
        print(f"配置文件不存在: {config_file}")
        print()


def example_json_config():
    """示例 4: 使用 JSON 配置文件"""
    print("=== 示例 4: 使用 JSON 配置文件 ===")
    
    config_file = '../common/config/litefs.json'
    
    if os.path.exists(config_file):
        app = Litefs(config_file=config_file)
        
        print(f"配置文件: {config_file}")
        print(f"Host: {app.config.host}")
        print(f"Port: {app.config.port}")
        print(f"Webroot: {app.config.webroot}")
        print(f"Debug: {app.config.debug}")
        print()
    else:
        print(f"配置文件不存在: {config_file}")
        print()


def example_toml_config():
    """示例 5: 使用 TOML 配置文件"""
    print("=== 示例 5: 使用 TOML 配置文件 ===")
    
    config_file = '../common/config/litefs.toml'
    
    if os.path.exists(config_file):
        app = Litefs(config_file=config_file)
        
        print(f"配置文件: {config_file}")
        print(f"Host: {app.config.host}")
        print(f"Port: {app.config.port}")
        print(f"Webroot: {app.config.webroot}")
        print(f"Debug: {app.config.debug}")
        print()
    else:
        print(f"配置文件不存在: {config_file}")
        print()


def example_env_config():
    """示例 6: 使用环境变量配置"""
    print("=== 示例 6: 使用环境变量配置 ===")
    
    os.environ['LITEFS_HOST'] = '0.0.0.0'
    os.environ['LITEFS_PORT'] = '8080'
    os.environ['LITEFS_DEBUG'] = 'true'
    os.environ['LITEFS_MAX_REQUEST_SIZE'] = '20971520'
    
    app = Litefs()
    
    print(f"Host: {app.config.host}")
    print(f"Port: {app.config.port}")
    print(f"Debug: {app.config.debug}")
    print(f"Max request size: {app.config.max_request_size}")
    print()
    
    del os.environ['LITEFS_HOST']
    del os.environ['LITEFS_PORT']
    del os.environ['LITEFS_DEBUG']
    del os.environ['LITEFS_MAX_REQUEST_SIZE']


def example_mixed_config():
    """示例 7: 混合配置（配置文件 + 环境变量 + 代码）"""
    print("=== 示例 7: 混合配置 ===")
    
    os.environ['LITEFS_DEBUG'] = 'true'
    
    config_file = '../common/config/litefs.yaml'
    
    if os.path.exists(config_file):
        app = Litefs(
            config_file=config_file,
            port=8080,
        )
        
        print(f"配置文件: {config_file}")
        print(f"Host: {app.config.host} (来自配置文件)")
        print(f"Port: {app.config.port} (来自代码)")
        print(f"Webroot: {app.config.webroot} (来自配置文件)")
        print(f"Debug: {app.config.debug} (来自环境变量)")
        print()
    else:
        print(f"配置文件不存在: {config_file}")
        print()
    
    del os.environ['LITEFS_DEBUG']


def example_config_object():
    """示例 8: 使用 Config 对象"""
    print("=== 示例 8: 使用 Config 对象 ===")
    
    config = Config()
    
    print(f"默认配置:")
    print(f"  Host: {config.host}")
    print(f"  Port: {config.port}")
    print(f"  Debug: {config.debug}")
    print()
    
    config.update(
        host='0.0.0.0',
        port=8080,
        debug=True,
    )
    
    print(f"更新后配置:")
    print(f"  Host: {config.host}")
    print(f"  Port: {config.port}")
    print(f"  Debug: {config.debug}")
    print()


def example_load_config_function():
    """示例 9: 使用 load_config 函数"""
    print("=== 示例 9: 使用 load_config 函数 ===")
    
    config_file = '../common/config/litefs.yaml'
    
    if os.path.exists(config_file):
        config = load_config(
            config_file=config_file,
            port=8080,
            debug=True,
        )
        
        print(f"Host: {config.host}")
        print(f"Port: {config.port}")
        print(f"Debug: {config.debug}")
        print()
    else:
        print(f"配置文件不存在: {config_file}")
        print()


def example_config_dict_operations():
    """示例 10: 配置字典操作"""
    print("=== 示例 10: 配置字典操作 ===")
    
    config = Config()
    
    print(f"所有配置键: {config.keys()}")
    print(f"所有配置值: {config.values()}")
    print(f"所有配置项: {config.items()}")
    print()
    
    print(f"'host' in config: {'host' in config}")
    print(f"'unknown' in config: {'unknown' in config}")
    print()
    
    print(f"转换为字典: {config.to_dict()}")
    print()


def example_config_get_set():
    """示例 11: 配置获取和设置"""
    print("=== 示例 11: 配置获取和设置 ===")
    
    config = Config()
    
    print(f"使用 get 方法: {config.get('host', 'default')}")
    print(f"使用属性访问: {config.host}")
    print()
    
    config.set('port', 8080)
    print(f"使用 set 方法后: {config.port}")
    print()
    
    config.debug = True
    print(f"使用属性设置后: {config.debug}")
    print()


def example_routing_with_config():
    """示例 12: 配置与路由系统配合使用"""
    print("=== 示例 12: 配置与路由系统配合使用 ===")
    
    # 创建配置对象
    config = Config(
        host='0.0.0.0',
        port=8080,
        debug=True
    )
    
    # 使用配置对象创建应用
    app = Litefs(config=config)
    
    # 定义路由处理函数
    @get('/hello', name='hello')
    def hello_handler(request):
        return f"Hello, World! (Debug: {app.config.debug})"
    
    @get('/config', name='config')
    def config_handler(request):
        return {
            "host": app.config.host,
            "port": app.config.port,
            "debug": app.config.debug,
            "webroot": app.config.webroot
        }
    
    # 注册路由
    app.register_routes(__name__)
    
    print(f"应用配置:")
    print(f"  Host: {app.config.host}")
    print(f"  Port: {app.config.port}")
    print(f"  Debug: {app.config.debug}")
    print()
    print(f"注册的路由:")
    for route in app.router.routes:
        print(f"  {route.path} ({', '.join(route.methods)}) - {route.name}")
    print()


def main():
    """运行所有示例"""
    print("=" * 60)
    print("Litefs 配置管理示例")
    print("=" * 60)
    print()
    
    example_default_config()
    example_code_config()
    example_yaml_config()
    example_json_config()
    example_toml_config()
    example_env_config()
    example_mixed_config()
    example_config_object()
    example_load_config_function()
    example_config_dict_operations()
    example_config_get_set()
    example_routing_with_config()
    
    print("=" * 60)
    print("所有示例运行完成")
    print("=" * 60)


if __name__ == '__main__':
    main()
