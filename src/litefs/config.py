#!/usr/bin/env python
# coding: utf-8

import os
import sys
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class Config:
    """
    配置管理类

    支持多种配置来源和分层管理：
    1. 默认配置（内置）
    2. 环境配置（如 config.production.yaml）
    3. 本地配置（如 config.local.yaml）
    4. 环境变量
    5. 代码中的配置

    配置优先级（从高到低）：
    代码配置 > 环境变量 > 本地配置 > 环境配置 > 默认值
    """

    DEFAULT_CONFIG = {
        # 服务器配置
        'host': 'localhost',              # 服务器绑定的主机地址
        'port': 9090,                     # 服务器监听的端口
        'debug': False,                   # 调试模式
        'log': './default.log',           # 日志文件路径
        'listen': 1024,                   # 最大监听连接数
        'max_request_size': 10485760,     # 最大请求大小（10MB）
        'max_upload_size': 52428800,      # 最大上传大小（50MB）
        'config_file': None,              # 配置文件路径
        'error_pages_dir': None,          # 错误页面目录
        'config_env': None,               # 环境名称（如 development, production）
        'default_page': 'index,index.html', # 默认页面
        
        # 缓存配置
        'cache_backend': 'tree',          # 缓存后端类型（memory, tree, redis, database, memcache）
        'cache_max_size': 10000,          # 内存缓存最大容量
        'cache_clean_period': 60,         # 缓存清理周期（秒）
        'cache_expiration_time': 3600,    # 缓存过期时间（秒）
        'file_cache_clean_period': 60,    # 文件缓存清理周期（秒）
        'file_cache_expiration_time': 3600, # 文件缓存过期时间（秒）
        
        # 会话配置
        'session_backend': 'memory',      # 会话后端类型（memory, redis, database, memcache）
        'session_max_size': 1000000,      # 会话最大容量
        'session_expiration_time': 3600,  # 会话过期时间（秒）
        'session_name': 'litefs.sid',     # 会话cookie名称
        'session_secure': False,          # 是否使用安全cookie
        'session_http_only': True,        # 是否仅HTTP访问
        'session_same_site': 'Lax',       # SameSite策略（Strict, Lax, None）
        
        # Redis 配置
        'redis_host': 'localhost',        # Redis 主机地址
        'redis_port': 6379,               # Redis 端口
        'redis_db': 0,                    # Redis 数据库编号
        'redis_password': None,           # Redis 密码
        'redis_key_prefix': 'litefs:',    # Redis 缓存键前缀
        'redis_session_key_prefix': 'litefs:session:', # Redis 会话键前缀
        
        # 数据库配置
        'database_url': None,             # 数据库连接 URL
        'database_session_table': 'sessions', # 会话表名
        'database_cache_table': 'cache',  # 缓存表名
        'database_pool_size': 10,         # 连接池大小
        'database_max_overflow': 20,      # 连接池最大溢出数
        'database_pool_timeout': 30,      # 连接池超时时间（秒）
        'database_pool_recycle': 3600,    # 连接回收时间（秒）
        
        # Memcache 配置
        'memcache_servers': 'localhost:11211', # Memcache 服务器列表
        'memcache_key_prefix': 'litefs:', # Memcache 缓存键前缀
        'memcache_session_key_prefix': 'litefs:session:', # Memcache 会话键前缀
        
        # Celery 任务队列配置
        'celery_broker': None,            # Celery Broker URL (如 redis://localhost:6379/0)
        'celery_backend': None,           # Celery Result Backend URL
        'celery_config': None,            # Celery 额外配置字典
        
        # 配置管理
        'config_encrypted_keys': [],      # 需要加密的配置键
        'config_secret_key': None,        # 配置加密密钥
    }

    ENV_PREFIX = 'LITEFS_'
    
    def __init__(self, config_file: Optional[str] = None, **kwargs):
        """
        初始化配置

        Args:
            config_file: 配置文件路径
            **kwargs: 其他配置项
        """
        self._config: Dict[str, Any] = {}
        self._config_files: List[str] = []  # 已加载的配置文件列表
        
        # 加载默认配置
        self._load_default_config()
        
        # 确定配置文件路径
        config_path = config_file or kwargs.get('config_file')
        
        # 加载分层配置
        if config_path:
            self._load_layered_configs(config_path)
        else:
            # 尝试自动加载配置文件
            self._load_auto_configs()
        
        # 加载环境变量
        self._load_env_vars()
        
        # 应用代码配置
        self._update_config(kwargs)
        
        # 验证配置
        self._validate_config()
    
    def _load_default_config(self):
        """加载默认配置"""
        self._config.update(self.DEFAULT_CONFIG.copy())
    
    def _load_auto_configs(self):
        """自动加载配置文件"""
        config_dir = Path('.')
        env = os.getenv(f'{self.ENV_PREFIX}CONFIG_ENV', 'development')
        
        # 尝试加载环境配置和本地配置
        env_config = config_dir / f'config.{env}.yaml'
        local_config = config_dir / 'config.local.yaml'
        
        if env_config.exists():
            self._load_config_file(str(env_config))
        
        if local_config.exists():
            self._load_config_file(str(local_config))
    
    def _load_layered_configs(self, config_file: str):
        """
        加载分层配置文件
        
        1. 基础配置文件（如 config.yaml）
        2. 环境配置文件（如 config.production.yaml）
        3. 本地配置文件（如 config.local.yaml）
        """
        config_path = Path(config_file)
        config_dir = config_path.parent
        base_name = config_path.stem
        ext = config_path.suffix
        
        # 加载基础配置
        if config_path.exists():
            self._load_config_file(str(config_path))
        
        # 加载环境配置
        env = os.getenv(f'{self.ENV_PREFIX}CONFIG_ENV', 'development')
        env_config = config_dir / f'{base_name}.{env}{ext}'
        if env_config.exists():
            self._load_config_file(str(env_config))
        
        # 加载本地配置
        local_config = config_dir / f'{base_name}.local{ext}'
        if local_config.exists():
            self._load_config_file(str(local_config))
    
    def _load_config_file(self, config_file: str):
        """
        加载配置文件

        支持的格式：YAML、JSON、TOML

        Args:
            config_file: 配置文件路径
        """
        config_path = Path(config_file)
        
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_file}")
        
        # 记录已加载的配置文件
        if str(config_path) not in self._config_files:
            self._config_files.append(str(config_path))
        
        file_ext = config_path.suffix.lower()
        
        if file_ext in ['.yaml', '.yml']:
            self._load_yaml_config(config_path)
        elif file_ext == '.json':
            self._load_json_config(config_path)
        elif file_ext in ['.toml', '.ini']:
            self._load_toml_config(config_path)
        else:
            raise ValueError(f"不支持的配置文件格式: {file_ext}")
    
    def _validate_config(self):
        """
        验证配置的有效性
        """
        # 验证缓存后端
        valid_cache_backends = ['memory', 'tree', 'redis', 'database', 'memcache']
        if self._config.get('cache_backend') not in valid_cache_backends:
            raise ValueError(f"无效的缓存后端: {self._config.get('cache_backend')}")
        
        # 验证会话后端
        valid_session_backends = ['memory', 'redis', 'database', 'memcache']
        if self._config.get('session_backend') not in valid_session_backends:
            raise ValueError(f"无效的会话后端: {self._config.get('session_backend')}")
        
        # 验证 SameSite 策略
        valid_same_site = ['Strict', 'Lax', 'None']
        if self._config.get('session_same_site') not in valid_same_site:
            raise ValueError(f"无效的 SameSite 策略: {self._config.get('session_same_site')}")
        
        # 验证端口
        port = self._config.get('port')
        if not isinstance(port, int) or port < 1 or port > 65535:
            raise ValueError(f"无效的端口: {port}")
    

    
    def encrypt_config(self, key: str, value: Any) -> str:
        """
        加密配置值
        
        Args:
            key: 配置键
            value: 配置值
            
        Returns:
            加密后的字符串
        """
        import base64
        from cryptography.fernet import Fernet
        
        secret_key = self._config.get('config_secret_key')
        if not secret_key:
            raise ValueError("配置加密密钥未设置")
        
        # 确保密钥长度正确
        if len(secret_key) < 32:
            secret_key = secret_key.ljust(32, '0')
        elif len(secret_key) > 32:
            secret_key = secret_key[:32]
        
        # 创建 Fernet 实例
        fernet = Fernet(base64.urlsafe_b64encode(secret_key.encode()))
        
        # 序列化值
        import json
        serialized_value = json.dumps(value)
        
        # 加密
        encrypted = fernet.encrypt(serialized_value.encode())
        
        return base64.b64encode(encrypted).decode()
    
    def decrypt_config(self, encrypted_value: str) -> Any:
        """
        解密配置值
        
        Args:
            encrypted_value: 加密后的字符串
            
        Returns:
            解密后的值
        """
        import base64
        from cryptography.fernet import Fernet
        
        secret_key = self._config.get('config_secret_key')
        if not secret_key:
            raise ValueError("配置加密密钥未设置")
        
        # 确保密钥长度正确
        if len(secret_key) < 32:
            secret_key = secret_key.ljust(32, '0')
        elif len(secret_key) > 32:
            secret_key = secret_key[:32]
        
        # 创建 Fernet 实例
        fernet = Fernet(base64.urlsafe_b64encode(secret_key.encode()))
        
        # 解密
        encrypted = base64.b64decode(encrypted_value.encode())
        decrypted = fernet.decrypt(encrypted)
        
        # 反序列化
        import json
        return json.loads(decrypted.decode())
    
    def _load_yaml_config(self, config_path: Path):
        """加载 YAML 配置文件"""
        try:
            import yaml
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                if config_data:
                    self._update_config(config_data)
        except ImportError:
            raise ImportError("需要安装 PyYAML: pip install pyyaml")
    
    def _load_json_config(self, config_path: Path):
        """加载 JSON 配置文件"""
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
            if config_data:
                self._update_config(config_data)
    
    def _load_toml_config(self, config_path: Path):
        """加载 TOML 配置文件"""
        try:
            import tomli
            with open(config_path, 'rb') as f:
                config_data = tomli.load(f)
                if config_data:
                    self._update_config(config_data)
        except ImportError:
            try:
                import tomllib
                with open(config_path, 'rb') as f:
                    config_data = tomllib.load(f)
                    if config_data:
                        self._update_config(config_data)
            except ImportError:
                raise ImportError("需要安装 tomli (Python < 3.11): pip install tomli")
    
    def _load_env_vars(self):
        """加载环境变量"""
        for key, default_value in self.DEFAULT_CONFIG.items():
            env_key = f"{self.ENV_PREFIX}{key.upper()}"
            env_value = os.getenv(env_key)
            
            if env_value is not None:
                self._config[key] = self._parse_env_value(env_value, default_value)
        
        # 处理 memcache_servers 配置，确保它是一个列表
        if isinstance(self._config.get('memcache_servers'), str):
            self._config['memcache_servers'] = [s.strip() for s in self._config['memcache_servers'].split(',')]
    
    def _parse_env_value(self, value: str, default_value: Any) -> Any:
        """
        解析环境变量值

        Args:
            value: 环境变量值
            default_value: 默认值，用于推断类型

        Returns:
            解析后的值
        """
        if isinstance(default_value, bool):
            return value.lower() in ('true', '1', 'yes', 'on')
        elif isinstance(default_value, int):
            return int(value)
        elif isinstance(default_value, float):
            return float(value)
        elif isinstance(default_value, list):
            return [v.strip() for v in value.split(',')]
        else:
            return value
    
    def _update_config(self, config_data: Dict[str, Any]):
        """
        更新配置

        Args:
            config_data: 配置数据
        """
        for key, value in config_data.items():
            if key in self.DEFAULT_CONFIG:
                # 检查是否需要解密
                if key in self._config.get('config_encrypted_keys', []) and isinstance(value, str):
                    try:
                        # 尝试解密
                        decrypted_value = self.decrypt_config(value)
                        self._config[key] = decrypted_value
                    except Exception:
                        # 解密失败，使用原始值
                        self._config[key] = value
                else:
                    self._config[key] = value
        
        # 处理 memcache_servers 配置，确保它是一个列表
        if isinstance(self._config.get('memcache_servers'), str):
            self._config['memcache_servers'] = [s.strip() for s in self._config['memcache_servers'].split(',')]
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项

        Args:
            key: 配置键
            default: 默认值

        Returns:
            配置值
        """
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        设置配置项

        Args:
            key: 配置键
            value: 配置值
        """
        if key in self.DEFAULT_CONFIG:
            self._config[key] = value
        else:
            raise ValueError(f"未知的配置项: {key}")
    
    def update(self, **kwargs):
        """
        批量更新配置

        Args:
            **kwargs: 配置项
        """
        for key, value in kwargs.items():
            self.set(key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典

        Returns:
            配置字典
        """
        return self._config.copy()
    
    def __getattr__(self, name: str) -> Any:
        """通过属性访问配置"""
        if name in self._config:
            return self._config[name]
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __setattr__(self, name: str, value: Any):
        """通过属性设置配置"""
        if name.startswith('_') or name == 'ENV_PREFIX':
            super().__setattr__(name, value)
        elif name in self.DEFAULT_CONFIG:
            self._config[name] = value
        else:
            raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")
    
    def __repr__(self) -> str:
        """字符串表示"""
        return f"Config({self._config})"
    
    def __contains__(self, key: str) -> bool:
        """检查配置项是否存在"""
        return key in self._config
    
    def keys(self) -> List[str]:
        """获取所有配置键"""
        return list(self._config.keys())
    
    def values(self) -> List[Any]:
        """获取所有配置值"""
        return list(self._config.values())
    
    def items(self) -> List[tuple]:
        """获取所有配置项"""
        return list(self._config.items())


def load_config(
    config_file: Optional[str] = None,
    env_prefix: Optional[str] = None,
    **kwargs
) -> Config:
    """
    加载配置

    Args:
        config_file: 配置文件路径
        env_prefix: 环境变量前缀（默认为 LITEFS_）
        **kwargs: 其他配置项

    Returns:
        Config 对象
    """
    config = Config(config_file=config_file, **kwargs)
    
    if env_prefix:
        config.ENV_PREFIX = env_prefix
        config._load_env_vars()
    
    return config


def merge_configs(*configs: Union[Config, Dict[str, Any]]) -> Config:
    """
    合并多个配置

    Args:
        *configs: 配置对象或字典

    Returns:
        合并后的 Config 对象
    """
    merged_config = Config.__new__(Config)
    merged_config._config = {}
    merged_config._config.update(merged_config.DEFAULT_CONFIG.copy())
    
    for config in configs:
        if isinstance(config, Config):
            merged_config._config.update(config.to_dict())
        elif isinstance(config, dict):
            merged_config._config.update(config)
    
    return merged_config
